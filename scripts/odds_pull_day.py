"""Pull one game day of Odds API history and compare credits to the estimate.

    uv run python scripts/odds_pull_day.py 2024-12-01 --dry-run   # plan + estimate only
    uv run python scripts/odds_pull_day.py 2024-12-01             # pull

Same calls the backfill makes for that day (see sportsquant.data.odds_backfill).
Already-saved responses cost 0.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date

import requests

from sportsquant.data.odds_api import OddsApiClient
from sportsquant.data.odds_backfill import CORE, calls_for_day, run_call
from sportsquant.data.odds_schedule import et_clock


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("day", type=date.fromisoformat)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", nargs="*", metavar="SPORT:PRODUCT",
                    help="e.g. americanfootball_nfl:props (default: the core plan)")
    a = ap.parse_args()
    pairs = [tuple(p.split(":")) for p in a.only] if a.only else CORE

    client = OddsApiClient.from_config(5_000_000)
    start_used = client.used
    plan = {}
    for sport, product in pairs:
        events = client.historical_events(sport, et_clock(a.day, 10)).body["data"]
        plan[f"{sport} {product}"] = calls_for_day(sport, product, a.day, events)

    print(f"Plan for {a.day} (remaining {client.remaining:,}):")
    for sport, calls in plan.items():
        print(f"  {sport:28s} {len(calls):3d} calls  expected {sum(c.expected for c in calls):6,}")
    if a.dry_run:
        return

    print("\nResult:")
    for sport, calls in plan.items():
        actual, cached, costs, errors = 0, 0, Counter(), []
        for call in calls:
            try:
                f = run_call(client, call)
            except requests.HTTPError as e:
                errors.append(f"{e.response.status_code} {call.args[:3]}")
                continue
            actual += f.credits_cost
            cached += f.cached
            if not f.cached:
                costs[f.credits_cost] += 1
        print(f"  {sport:28s} expected {sum(c.expected for c in calls):6,}  actual {actual:6,}"
              f"  cached {cached}  per-call costs {dict(costs)}")
        for err in errors:
            print(f"    error {err}")
    print(f"  headers: used {start_used:,} -> {client.used:,} (+{client.used - start_used:,}),"
          f" remaining {client.remaining:,}")


if __name__ == "__main__":
    main()
