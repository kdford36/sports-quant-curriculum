"""Plan the Odds API backfill: which days, which calls, what they cost.

The plan is built from cheap game lists (1 credit per sport per day, at 10 AM ET):

- NBA props (us): one call per game at 10 AM ET (early price) and at tip-off (closing).
- NFL and CBB lines (us + eu): one sport-wide snapshot per start-time slot (closing).

Each snapshot is requested *at* a start time; the API returns the latest snapshot at or
before it, so a closing line never looks ahead. Batches are (sport, season).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta

from sportsquant.data.odds_api import OddsApiClient, estimate_cost, raw_path
from sportsquant.data.odds_schedule import et_clock, games_on, parse_utc, start_slots

NBA_PROPS = ["player_points", "player_rebounds", "player_assists", "player_threes",
             "player_points_rebounds_assists"]
LINES = ["h2h", "spreads", "totals"]

PROPS_START = date(2023, 5, 3)  # first day of historical player props

# In-season windows, generous on both ends (an empty day costs only its 1-credit game list).
# None as the end means "through yesterday".
SEASONS: dict[str, list[tuple[str, str | None]]] = {
    "basketball_nba": [("2023-05-03", "2023-06-30"), ("2023-10-01", "2024-06-30"),
                       ("2024-10-01", "2025-06-30"), ("2025-10-01", "2026-06-30"),
                       ("2026-10-01", None)],
    "basketball_ncaab": [("2020-11-25", "2021-04-10"), ("2021-11-01", "2022-04-10"),
                         ("2022-11-01", "2023-04-10"), ("2023-11-01", "2024-04-10"),
                         ("2024-11-01", "2025-04-10"), ("2025-11-01", "2026-04-10"),
                         ("2026-11-01", None)],
    "americanfootball_nfl": [("2020-09-01", "2021-02-15"), ("2021-09-01", "2022-02-15"),
                             ("2022-09-01", "2023-02-15"), ("2023-09-01", "2024-02-15"),
                             ("2024-09-01", "2025-02-15"), ("2025-09-01", "2026-02-15"),
                             ("2026-09-01", None)],
}


@dataclass(frozen=True)
class Call:
    kind: str  # "event_odds" (one game's props) or "odds" (sport-wide game lines)
    args: tuple
    expected: int


@dataclass(frozen=True)
class Batch:
    sport: str
    start: date
    end: date

    @property
    def name(self) -> str:
        """Season label: a window starting Jan-Jun belongs to the season that began last year."""
        y = self.start.year - (self.start.month < 7)
        return f"{self.sport} {y}-{str(y + 1)[2:]}"

    def days(self) -> Iterator[date]:
        d = self.start
        while d <= self.end:
            yield d
            d += timedelta(days=1)


def batches(yesterday: date, sports: list[str] | None = None) -> list[Batch]:
    out = []
    for sport, windows in SEASONS.items():
        if sports and sport not in sports:
            continue
        for start, end in windows:
            s = date.fromisoformat(start)
            e = min(date.fromisoformat(end), yesterday) if end else yesterday
            if s <= e:
                out.append(Batch(sport, s, e))
    return out


def calls_for_day(sport: str, day: date, events: list[dict]) -> list[Call]:
    """The paid calls for one sport on one game day, given that morning's game list."""
    todays = games_on(events, day)
    if sport == "basketball_nba":
        if day < PROPS_START:
            return []
        cost = estimate_cost("historical_event_odds", NBA_PROPS, ["us"])
        morning = et_clock(day, 10)
        out = []
        for g in todays:
            for when in (morning, g["commence_time"]):
                if parse_utc(when) <= parse_utc(g["commence_time"]):
                    out.append(Call("event_odds", (sport, g["id"], when, NBA_PROPS, ["us"]),
                                    cost))
        return out
    cost = estimate_cost("historical_odds", LINES, ["us", "eu"])
    return [Call("odds", (sport, slot, LINES, ["us", "eu"]), cost)
            for slot in start_slots(todays)]


def plan_batch(client: OddsApiClient, batch: Batch) -> list[Call]:
    """Fetch (or read cached) each day's game list and return the batch's paid calls."""
    calls = []
    for day in batch.days():
        events = client.historical_events(batch.sport, et_clock(day, 10)).body["data"]
        calls.extend(calls_for_day(batch.sport, day, events))
    return calls


def call_path(client: OddsApiClient, call: Call):
    """Where this call's raw file lives (exists -> already paid for, costs 0)."""
    if call.kind == "event_odds":
        sport, event_id, when, markets, regions = call.args
        return raw_path(client.raw_root, sport, "historical_event_odds", when, event_id,
                        markets, regions)
    sport, when, markets, regions = call.args
    return raw_path(client.raw_root, sport, "historical_odds", when, None, markets, regions)


def run_call(client: OddsApiClient, call: Call):
    fetch = (client.historical_event_odds if call.kind == "event_odds"
             else client.historical_odds)
    return fetch(*call.args)
