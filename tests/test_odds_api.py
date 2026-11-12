"""Tests for the Odds API client. No network: a fake session stands in for requests."""

from __future__ import annotations

import gzip
import json

import pytest

from sportsquant.data.odds_api import (
    CreditFloorError,
    OddsApiClient,
    estimate_cost,
    raw_path,
)

NBA_PROPS = ["player_points", "player_rebounds", "player_assists", "player_threes",
             "player_points_rebounds_assists"]


class FakeResponse:
    def __init__(self, body, headers, status=200):
        self._body, self.headers, self.status_code = body, headers, status

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Records each call; answers with a fixed body and credit headers."""

    def __init__(self, remaining=5_000_000, status=200):
        self.calls, self.remaining, self.used, self.status = [], remaining, 0, status

    def get(self, url, params, timeout):
        self.calls.append((url, params))
        cost = estimate_cost(
            "historical_events" if url.endswith("/events") else "historical_odds",
            params.get("markets", "").split(",") if "markets" in params else None,
            params.get("regions", "").split(",") if "regions" in params else None,
        )
        self.used += cost
        self.remaining -= cost
        headers = {"x-requests-last": str(cost), "x-requests-used": str(self.used),
                   "x-requests-remaining": str(self.remaining)}
        return FakeResponse({"timestamp": params.get("date"), "data": [{"id": "abc"}]}, headers,
                            self.status)


def make_client(tmp_path, **session_kwargs):
    session = FakeSession(**session_kwargs)
    return OddsApiClient("SECRET", tmp_path, plan_credits=5_000_000, session=session), session


def test_estimate_cost_matches_published_pricing():
    assert estimate_cost("historical_events") == 1
    assert estimate_cost("historical_event_odds", NBA_PROPS, ["us"]) == 50
    assert estimate_cost("historical_odds", ["h2h", "spreads", "totals"], ["us", "eu"]) == 60
    assert estimate_cost("odds", ["h2h"], ["us"]) == 1


def test_raw_path_is_windows_safe_and_order_independent(tmp_path):
    a = raw_path(tmp_path, "basketball_nba", "historical_odds", "2024-12-01T16:00:00Z",
                 markets=["h2h", "totals"], regions=["us", "eu"])
    b = raw_path(tmp_path, "basketball_nba", "historical_odds", "2024-12-01T16:00:00Z",
                 markets=["totals", "h2h"], regions=["eu", "us"])
    assert a == b
    assert ":" not in a.name
    assert a.parent.name == "2024-12-01"


def test_first_call_saves_gzipped_raw_without_key(tmp_path):
    client, _ = make_client(tmp_path)
    f = client.historical_events("basketball_nba", "2024-12-01T16:00:00Z")
    assert not f.cached and f.credits_cost == 1
    with gzip.open(f.path, "rt") as fh:
        saved = json.load(fh)
    assert saved["body"] == f.body
    assert "SECRET" not in f.path.read_bytes().decode("latin-1")
    assert "SECRET" not in json.dumps(saved)


def test_second_identical_call_is_free_and_skips_network(tmp_path):
    client, session = make_client(tmp_path)
    args = ("basketball_nba", "evt1", "2024-12-01T16:00:00Z", NBA_PROPS, ["us"])
    first = client.historical_event_odds(*args)
    second = client.historical_event_odds(*args)
    assert len(session.calls) == 1
    assert second.cached and second.credits_cost == 0 and second.body == first.body
    assert client.summary()["spent_this_run"] == 50


def test_credit_headers_tracked_and_logged(tmp_path):
    client, _ = make_client(tmp_path)
    client.historical_odds("americanfootball_nfl", "2024-12-01T16:00:00Z",
                           ["h2h", "spreads", "totals"], ["us", "eu"])
    assert client.remaining == 5_000_000 - 60
    log = (tmp_path / "_credit_log.jsonl").read_text().strip().splitlines()
    assert json.loads(log[0])["cost"] == 60


def test_stops_before_crossing_floor(tmp_path):
    # Floor is 10% of 5M = 500,000. Start just above it.
    client, session = make_client(tmp_path, remaining=500_040)
    client.historical_events("basketball_nba", "2024-12-01T16:00:00Z")  # learns remaining
    with pytest.raises(CreditFloorError):
        client.historical_event_odds("basketball_nba", "evt1", "2024-12-01T16:00:00Z",
                                     NBA_PROPS, ["us"])
    assert len(session.calls) == 1


def test_error_response_saves_nothing(tmp_path):
    client, _ = make_client(tmp_path, status=422)
    with pytest.raises(RuntimeError):
        client.historical_events("basketball_nba", "2024-12-01T16:00:00Z")
    assert not list(tmp_path.rglob("*.json.gz"))


def test_sync_credits_arms_floor_before_first_paid_call(tmp_path):
    # Without sync, remaining is None and the first paid call goes through unchecked.
    client, session = make_client(tmp_path, remaining=500_040)
    client.sync_credits()  # free /sports call loads remaining = 500,040
    assert client.remaining == 500_040
    with pytest.raises(CreditFloorError):
        client.historical_event_odds("basketball_nba", "evt1", "2024-12-01T16:00:00Z",
                                     NBA_PROPS, ["us"])
    assert len(session.calls) == 1  # only the free call went out


class RateLimitedSession(FakeSession):
    """Answers 429 for the first ``n_limited`` calls, then behaves normally."""

    def __init__(self, n_limited, **kwargs):
        super().__init__(**kwargs)
        self.n_limited = n_limited

    def get(self, url, params, timeout):
        if len(self.calls) < self.n_limited:
            self.calls.append((url, params))
            return FakeResponse({}, {}, status=429)
        return super().get(url, params, timeout)


def test_retries_on_429_with_backoff(tmp_path):
    waits = []
    session = RateLimitedSession(n_limited=2)
    client = OddsApiClient("SECRET", tmp_path, plan_credits=5_000_000, session=session,
                           sleep=waits.append)
    f = client.historical_events("basketball_nba", "2024-12-01T16:00:00Z")
    assert waits == [1, 2]
    assert len(session.calls) == 3 and f.credits_cost == 1


def test_gives_up_after_max_retries_and_saves_nothing(tmp_path):
    session = RateLimitedSession(n_limited=99)
    client = OddsApiClient("SECRET", tmp_path, plan_credits=5_000_000, session=session,
                           sleep=lambda s: None, max_retries=2)
    with pytest.raises(RuntimeError, match="429"):
        client.historical_events("basketball_nba", "2024-12-01T16:00:00Z")
    assert len(session.calls) == 3
    assert not list(tmp_path.rglob("*.json.gz"))
