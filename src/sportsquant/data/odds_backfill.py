"""Plan the Odds API backfill: which days, which calls, what they cost.

The plan is built from cheap game lists (1 credit per sport per day; 10 AM ET, or 4 AM ET
for soccer so early European kickoffs are still listed). Products:

- lines: one sport-wide snapshot per start-time slot (closing). US sports us + eu
  (Pinnacle); soccer eu + uk (Pinnacle, Betfair exchange).
- props (sportsbooks, us): one call per game at 10 AM ET (game day for NBA, the day
  before for NFL and soccer) and at the start (closing).

Each snapshot is requested *at* a time; the API returns the latest snapshot at or before
it, so a closing line never looks ahead. Batches are (sport, product, season).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta

from sportsquant.data.odds_api import OddsApiClient, estimate_cost, raw_path
from sportsquant.data.odds_schedule import et_clock, games_on, parse_utc, start_slots

NBA_PROPS = ["player_points", "player_rebounds", "player_assists", "player_threes",
             "player_points_rebounds_assists"]
NFL_PROPS = ["player_pass_yds", "player_pass_tds", "player_pass_attempts",
             "player_pass_completions", "player_pass_interceptions", "player_rush_yds",
             "player_rush_attempts", "player_receptions", "player_reception_yds",
             "player_anytime_td"]
SOCCER_PROPS = ["player_goal_scorer_anytime", "player_shots", "player_shots_on_target",
                "player_assists", "player_to_receive_card"]
LINES = ["h2h", "spreads", "totals"]

SOCCER = ["soccer_epl", "soccer_spain_la_liga", "soccer_uefa_champs_league"]

# Props per sport: (markets, days before game day for the early 10 AM ET snapshot).
# NFL and soccer early prices come the day before: game-day 10 AM ET is too close to
# a 1 PM NFL kickoff and after most European kickoffs.
PROPS = {"basketball_nba": (NBA_PROPS, 0), "americanfootball_nfl": (NFL_PROPS, 1),
         **{s: (SOCCER_PROPS, 1) for s in SOCCER}}
PROPS_REGIONS = ["us"]

PROPS_START = date(2023, 5, 3)  # first day of historical player props


def lines_regions(sport: str) -> list[str]:
    return ["eu", "uk"] if sport.startswith("soccer_") else ["us", "eu"]


def list_hour(sport: str) -> int:
    """ET hour of the daily game list: before the day's first start."""
    return 4 if sport.startswith("soccer_") else 10


def _seasons(first: int, start: str, end: str, last: int = 2025):
    """Windows first..last (start mm-dd to next year's end mm-dd), then the current season
    through yesterday."""
    return ([(f"{y}-{start}", f"{y + 1}-{end}") for y in range(first, last + 1)]
            + [(f"{last + 1}-{start}", None)])


# In-season windows per (sport, product), generous on both ends (an empty day costs only
# its 1-credit game list, an empty props call costs 0). None as the end means "through
# yesterday". Game lines exist from June 2020, props from 2023-05-03.
_NBA_FROM_2023 = _seasons(2023, "10-01", "06-30")
PLANS: dict[tuple[str, str], list[tuple[str, str | None]]] = {
    # Core plan, approved 2026-11-12.
    ("basketball_nba", "props"): [("2023-05-03", "2023-06-30"), *_NBA_FROM_2023],
    ("basketball_ncaab", "lines"): [("2020-11-25", "2021-04-10"),
                                    *_seasons(2021, "11-01", "04-10")],
    ("americanfootball_nfl", "lines"): _seasons(2020, "09-01", "02-15"),
    # 2026-11-12: NBA lines from the 2020 bubble restart; NFL props.
    ("basketball_nba", "lines"): [("2020-07-22", "2020-10-15"), ("2020-12-01", "2021-07-25"),
                                  ("2021-10-01", "2022-06-30"), ("2022-10-01", "2023-06-30"),
                                  *_NBA_FROM_2023],
    ("americanfootball_nfl", "props"): _seasons(2023, "09-01", "02-15"),
    # 2026-11-15: CFB lines, week 0 (late Aug) through the CFP title game (Jan).
    ("americanfootball_ncaaf", "lines"): [("2020-08-25", "2021-01-20"),
                                          *_seasons(2021, "08-20", "01-25")],
    # 2026-11-15: soccer lines from the June 2020 restart (2020 UCL final eight in August).
    ("soccer_epl", "lines"): [("2020-06-10", "2020-07-31"), ("2020-09-05", "2021-05-31"),
                              *_seasons(2021, "08-01", "05-31")],
    ("soccer_spain_la_liga", "lines"): [("2020-06-05", "2020-07-31"),
                                        ("2020-09-05", "2021-05-31"),
                                        *_seasons(2021, "08-01", "06-05")],
    ("soccer_uefa_champs_league", "lines"): [("2020-07-31", "2020-08-31"),
                                             ("2020-10-15", "2021-06-05"),
                                             *_seasons(2021, "09-01", "06-05")],
    # 2026-11-15: soccer props (us books) from the end of 2022-23.
    ("soccer_epl", "props"): [("2023-05-03", "2023-05-31"), *_seasons(2023, "08-01", "05-31")],
    ("soccer_spain_la_liga", "props"): [("2023-05-03", "2023-06-05"),
                                        *_seasons(2023, "08-01", "06-05")],
    ("soccer_uefa_champs_league", "props"): [("2023-05-03", "2023-06-15"),
                                             *_seasons(2023, "09-01", "06-05")],
    # Pick'em props (us_dfs region: PrizePicks, Underdog; from 2024-25) were priced and
    # dropped 2026-11-15. They are not DFS salary data.
}
# What the one-day test pull (scripts/odds_pull_day.py) covers: the original core plan.
CORE = [("basketball_nba", "props"), ("basketball_ncaab", "lines"),
        ("americanfootball_nfl", "lines")]


@dataclass(frozen=True)
class Call:
    kind: str  # "event_odds" (one game's props) or "odds" (sport-wide game lines)
    args: tuple
    expected: int


@dataclass(frozen=True)
class Batch:
    sport: str
    product: str  # "lines" or "props"
    start: date
    end: date

    @property
    def name(self) -> str:
        """Season label: a window starting Jan-Jul belongs to the season that began last year
        (the 2020 NBA bubble restart in July is 2019-20)."""
        y = self.start.year - (self.start.month < 8)
        return f"{self.sport} {self.product} {y}-{str(y + 1)[2:]}"

    def days(self) -> Iterator[date]:
        d = self.start
        while d <= self.end:
            yield d
            d += timedelta(days=1)


def batches(yesterday: date, sports: list[str] | None = None,
            products: list[str] | None = None) -> list[Batch]:
    out = []
    for (sport, product), windows in PLANS.items():
        if (sports and sport not in sports) or (products and product not in products):
            continue
        for start, end in windows:
            s = date.fromisoformat(start)
            e = min(date.fromisoformat(end), yesterday) if end else yesterday
            if s <= e:
                out.append(Batch(sport, product, s, e))
    return out


def calls_for_day(sport: str, product: str, day: date, events: list[dict]) -> list[Call]:
    """The paid calls for one product on one game day, given that morning's game list."""
    todays = games_on(events, day)
    if product == "props":
        if day < PROPS_START:
            return []
        markets, days_before = PROPS[sport]
        regions = PROPS_REGIONS
        cost = estimate_cost("historical_event_odds", markets, regions)
        early = et_clock(day - timedelta(days=days_before), 10)
        out = []
        # A day-before snapshot can fall before props history starts (the API answers 422).
        first = [early] if parse_utc(early).date() >= PROPS_START else []
        for g in todays:
            for when in (*first, g["commence_time"]):
                if parse_utc(when) <= parse_utc(g["commence_time"]):
                    out.append(Call("event_odds", (sport, g["id"], when, markets, regions),
                                    cost))
        return out
    regions = lines_regions(sport)
    cost = estimate_cost("historical_odds", LINES, regions)
    return [Call("odds", (sport, slot, LINES, regions), cost) for slot in start_slots(todays)]


def plan_batch(client: OddsApiClient, batch: Batch) -> list[Call]:
    """Fetch (or read cached) each day's game list and return the batch's paid calls.

    Props plan each game once, from the last day it was listed: one day's
    list can repeat a game (the API did on 2025-01-05 NFL), and a moved game shows up in
    two days' lists.
    """
    calls = []
    latest: dict[str, tuple[date, dict]] = {}
    hour = list_hour(batch.sport)
    for day in batch.days():
        events = client.historical_events(batch.sport, et_clock(day, hour)).body["data"]
        if batch.product == "props":
            for g in games_on(events, day):
                latest[g["id"]] = (day, g)
        else:
            calls.extend(calls_for_day(batch.sport, batch.product, day, events))
    for day, g in sorted(latest.values(), key=lambda dg: (dg[0], dg[1]["commence_time"])):
        calls.extend(calls_for_day(batch.sport, batch.product, day, [g]))
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
