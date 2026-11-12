"""Client for The Odds API (v4), built for a paid historical backfill.

Three rules drive the design (see CLAUDE.md, "The Odds API"):

1. Save every raw response, gzipped, before parsing. A paid call is never repeated.
2. Skip any request whose raw file already exists, so a pull can stop and resume.
3. Track credits from the response headers and stop before the plan runs low.

Usage:

    from sportsquant.data.odds_api import OddsApiClient
    client = OddsApiClient.from_config(plan_credits=5_000_000)
    events = client.historical_events("basketball_nba", "2024-12-01T16:00:00Z")

Every public fetch method returns a ``Fetch``: the parsed body, whether it came
from disk (``cached``) and the credits the call cost (0 when cached).
"""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

BASE_URL = "https://api.the-odds-api.com/v4"

# Credit multiplier per endpoint kind: cost = multiplier × markets × regions.
# ``historical_events`` is a flat 1 credit, so it has no markets or regions.
_HISTORICAL_MULTIPLIER = 10


class CreditFloorError(RuntimeError):
    """Raised before a call that would push remaining credits below the floor."""


@dataclass(frozen=True)
class Fetch:
    body: Any
    cached: bool
    credits_cost: int  # from headers (x-requests-last); 0 when served from disk
    path: Path


def estimate_cost(endpoint: str, markets: list[str] | None = None,
                  regions: list[str] | None = None) -> int:
    """Expected credits for one call, per The Odds API's published pricing."""
    if endpoint == "historical_events":
        return 1
    n = len(markets or []) * len(regions or [])
    if endpoint in ("historical_odds", "historical_event_odds"):
        return _HISTORICAL_MULTIPLIER * n
    if endpoint in ("odds", "event_odds"):
        return n
    raise ValueError(f"unknown endpoint: {endpoint}")


def _snapshot_stamp(date: str) -> str:
    """'2024-12-01T16:00:00Z' -> '20241201T160000Z' (no colons: Windows-safe)."""
    dt = datetime.fromisoformat(date)
    if dt.tzinfo is None:  # a naive time would silently be read as this machine's local zone
        raise ValueError(f"snapshot date needs a timezone, e.g. '...Z': {date!r}")
    dt = dt.astimezone(UTC)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def raw_path(root: Path, sport: str, endpoint: str, date: str, event_id: str | None = None,
             markets: list[str] | None = None, regions: list[str] | None = None) -> Path:
    """Where one request's raw response lives. Same request -> same path, always.

    Layout: root/sport/endpoint/YYYY-MM-DD/<event>__<stamp>[__<regions>__m<hash>].json.gz

    Markets are hashed (sorted first, so order does not matter) to keep paths short;
    the full list is stored inside the file.
    """
    stamp = _snapshot_stamp(date)
    name = f"{event_id or 'all'}__{stamp}"
    if markets or regions:
        mkey = ",".join(sorted(markets or []))
        mhash = hashlib.sha1(mkey.encode()).hexdigest()[:8]
        name += f"__{'+'.join(sorted(regions or []))}__m{mhash}"
    return root / sport / endpoint / f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}" / f"{name}.json.gz"


class OddsApiClient:
    def __init__(self, api_key: str, raw_root: Path, plan_credits: int,
                 floor_frac: float = 0.10, session: requests.Session | None = None,
                 base_url: str = BASE_URL, timeout: float = 30.0):
        self._api_key = api_key
        self.raw_root = Path(raw_root)
        self.plan_credits = plan_credits
        self.floor = int(plan_credits * floor_frac)
        self.session = session or requests.Session()
        self.base_url = base_url
        self.timeout = timeout
        # Credit state, updated from every live response's headers.
        self.remaining: int | None = None
        self.used: int | None = None
        self.spent_this_run = 0
        self.calls_live = 0
        self.calls_cached = 0

    @classmethod
    def from_config(cls, plan_credits: int, **kwargs) -> OddsApiClient:
        from sportsquant import config

        return cls(config.odds_api_key(), config.raw_dir("odds_api"), plan_credits, **kwargs)

    # ---- public endpoints -------------------------------------------------

    def historical_events(self, sport: str, date: str) -> Fetch:
        """Games that existed at ``date`` (closest snapshot at or before it). 1 credit."""
        return self._get(f"/historical/sports/{sport}/events", sport, "historical_events",
                         date, params={"date": date})

    def historical_odds(self, sport: str, date: str, markets: list[str],
                        regions: list[str]) -> Fetch:
        """Game-line snapshot for every game in a sport. 10 × markets × regions."""
        return self._get(f"/historical/sports/{sport}/odds", sport, "historical_odds", date,
                         params=self._odds_params(date, markets, regions),
                         markets=markets, regions=regions)

    def historical_event_odds(self, sport: str, event_id: str, date: str, markets: list[str],
                              regions: list[str]) -> Fetch:
        """Snapshot for one game (use for player props). 10 × markets × regions."""
        return self._get(f"/historical/sports/{sport}/events/{event_id}/odds", sport,
                         "historical_event_odds", date,
                         params=self._odds_params(date, markets, regions),
                         event_id=event_id, markets=markets, regions=regions)

    def summary(self) -> dict[str, int | None]:
        return {"live_calls": self.calls_live, "cached_calls": self.calls_cached,
                "spent_this_run": self.spent_this_run, "used": self.used,
                "remaining": self.remaining}

    # ---- internals --------------------------------------------------------

    @staticmethod
    def _odds_params(date: str, markets: list[str], regions: list[str]) -> dict[str, str]:
        return {"date": date, "markets": ",".join(markets), "regions": ",".join(regions),
                "oddsFormat": "american", "dateFormat": "iso"}

    def _get(self, url_path: str, sport: str, endpoint: str, date: str,
             params: dict[str, str], event_id: str | None = None,
             markets: list[str] | None = None, regions: list[str] | None = None) -> Fetch:
        path = raw_path(self.raw_root, sport, endpoint, date, event_id, markets, regions)

        # Rule 2: already have it -> read from disk, spend nothing.
        if path.exists():
            self.calls_cached += 1
            with gzip.open(path, "rt", encoding="utf-8") as f:
                return Fetch(json.load(f)["body"], cached=True, credits_cost=0, path=path)

        # Rule 3: refuse a call that could cross the floor.
        expected = estimate_cost(endpoint, markets, regions)
        if self.remaining is not None and self.remaining - expected < self.floor:
            raise CreditFloorError(
                f"{self.remaining:,} credits left; a {expected}-credit call would cross "
                f"the floor of {self.floor:,}. Stopping."
            )

        resp = self.session.get(self.base_url + url_path,
                                params={**params, "apiKey": self._api_key},
                                timeout=self.timeout)
        self._read_credit_headers(resp.headers)
        resp.raise_for_status()  # nothing is saved for an error response
        body = resp.json()

        # Rule 1: save raw before anyone parses it. Key is never written to disk.
        envelope = {
            "request": {"path": url_path, "params": params},
            "fetched_at": datetime.now(UTC).isoformat(),
            "credits": {"last": _int(resp.headers.get("x-requests-last")),
                        "used": self.used, "remaining": self.remaining},
            "body": body,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(envelope, f)
        tmp.replace(path)  # atomic: a crash never leaves a half-written file that looks done

        cost = _int(resp.headers.get("x-requests-last")) or 0
        self.calls_live += 1
        self.spent_this_run += cost
        self._log(endpoint, sport, event_id, date, expected, cost)
        return Fetch(body, cached=False, credits_cost=cost, path=path)

    def _read_credit_headers(self, headers) -> None:
        if (rem := _int(headers.get("x-requests-remaining"))) is not None:
            self.remaining = rem
        if (used := _int(headers.get("x-requests-used"))) is not None:
            self.used = used

    def _log(self, endpoint, sport, event_id, date, expected, cost) -> None:
        """One JSON line per live call, next to the raw files."""
        line = {"at": datetime.now(UTC).isoformat(), "endpoint": endpoint, "sport": sport,
                "event_id": event_id, "date": date, "expected": expected, "cost": cost,
                "used": self.used, "remaining": self.remaining}
        self.raw_root.mkdir(parents=True, exist_ok=True)
        with open(self.raw_root / "_credit_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")


def _int(value: str | None) -> int | None:
    try:
        return int(float(value)) if value is not None else None
    except ValueError:
        return None
