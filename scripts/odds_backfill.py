"""Run the Odds API historical backfill in (sport, season) batches.

    uv run python scripts/odds_backfill.py --plan-only               # game lists only, exact cost
    uv run python scripts/odds_backfill.py --max-credits 1280000     # pull, batch by batch
    uv run python scripts/odds_backfill.py --plan-only --sports basketball_nba --products lines

Safe to stop and rerun: anything already saved is read from disk and costs 0.
Each finished batch appends one line to <raw odds dir>/_batch_log.jsonl.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, date, datetime, timedelta

import requests

from sportsquant.data.odds_api import CreditFloorError, OddsApiClient
from sportsquant.data.odds_backfill import batches, call_path, plan_batch, run_call

PLAN_CREDITS = 5_000_000
MAX_CONSECUTIVE_ERRORS = 25


def say(msg: str) -> None:
    print(msg, flush=True)


def build_plans(client, sports, products):
    yesterday = date.today() - timedelta(days=1)
    plans = []
    say(f"Game lists through {yesterday} (remaining {client.remaining:,})")
    for b in batches(yesterday, sports, products):
        before = client.spent_this_run
        calls = plan_batch(client, b)
        todo = [c for c in calls if not call_path(client, c).exists()]
        cost = sum(c.expected for c in todo)
        plans.append((b, calls, todo))
        say(f"  {b.name:36s} lists {client.spent_this_run - before:4d}cr  calls {len(calls):6,}"
            f"  to pull {len(todo):6,}  est {cost:9,}")
    total = sum(c.expected for _, _, todo in plans for c in todo)
    say(f"  {'TOTAL to pull':36s} {sum(len(t) for _, _, t in plans):38,}  est {total:9,}")
    say(f"  game lists cost this run: {client.spent_this_run:,}; remaining {client.remaining:,}")
    return plans, total


def run_batch(client, batch, todo, max_credits, log_path):
    start_spent, start_t = client.spent_this_run, time.time()
    errors, consecutive = [], 0
    for i, call in enumerate(todo, 1):
        if client.spent_this_run + call.expected > max_credits:
            raise SystemExit(f"Stopping: next call would pass --max-credits {max_credits:,}.")
        for attempt in range(4):
            try:
                run_call(client, call)
                consecutive = 0
                break
            except requests.HTTPError as e:
                errors.append({"status": e.response.status_code, "args": list(call.args[:3])})
                consecutive += 1
                break
            except requests.RequestException as e:  # network hiccup: wait and retry
                if attempt == 3:
                    raise SystemExit(f"Network failing, stopping (rerun to resume): {e}")
                time.sleep(10 * (attempt + 1))
        if consecutive >= MAX_CONSECUTIVE_ERRORS:
            raise SystemExit(f"{consecutive} errors in a row, stopping. Last: {errors[-1]}")
        if i % 500 == 0:
            say(f"    {batch.name}: {i:,}/{len(todo):,} calls, remaining {client.remaining:,}")
    line = {"at": datetime.now(UTC).isoformat(), "batch": batch.name, "calls": len(todo),
            "expected": sum(c.expected for c in todo),
            "spent": client.spent_this_run - start_spent, "errors": len(errors),
            "error_sample": errors[:5], "used": client.used, "remaining": client.remaining,
            "minutes": round((time.time() - start_t) / 60, 1)}
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")
    say(f"  DONE {batch.name:36s} spent {line['spent']:9,} / est {line['expected']:9,}"
        f"  errors {len(errors):4d}  remaining {client.remaining:,}  ({line['minutes']} min)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--max-credits", type=int, help="hard cap on credits spent this run")
    ap.add_argument("--sports", nargs="*", help="limit to these sport keys")
    ap.add_argument("--products", nargs="*", choices=["props", "lines"],
                    help="limit to these products")
    a = ap.parse_args()
    if not a.plan_only and not a.max_credits:
        sys.exit("Pulling needs --max-credits (the approved budget).")

    client = OddsApiClient.from_config(PLAN_CREDITS)
    plans, total = build_plans(client, a.sports, a.products)
    if a.plan_only:
        return
    if total > a.max_credits:
        sys.exit(f"Plan ({total:,}) exceeds --max-credits ({a.max_credits:,}); not starting.")

    log_path = client.raw_root / "_batch_log.jsonl"
    say("\nPulling:")
    try:
        for batch, _, todo in plans:
            if todo:
                run_batch(client, batch, todo, a.max_credits, log_path)
    except CreditFloorError as e:
        sys.exit(str(e))
    say(f"\nFinished. This run: {client.summary()}")


if __name__ == "__main__":
    main()
