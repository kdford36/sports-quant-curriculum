"""Check this machine's setup: paths from .env and a free Odds API call.

Run from the repo root:  uv run python scripts/check_setup.py

The /sports endpoint costs 0 credits, but its response headers still report the
account's credit balance, so this confirms the key and the active plan for free.
The key itself is never printed.
"""

from __future__ import annotations

import requests

from sportsquant import config


def main() -> None:
    print(f"DATA_DIR  -> {config.data_dir()}")
    print(f"raw odds  -> {config.raw_dir('odds_api')}")
    print(f"DB_PATH   -> {config.db_path()}")

    key = config.odds_api_key()
    resp = requests.get("https://api.the-odds-api.com/v4/sports",
                        params={"apiKey": key}, timeout=30)
    if resp.status_code == 401:
        raise SystemExit("Odds API rejected the key (401). Re-check ODDS_API_KEY in .env.")
    resp.raise_for_status()

    keys = {s["key"] for s in resp.json()}
    used = resp.headers.get("x-requests-used")
    remaining = resp.headers.get("x-requests-remaining")
    print(f"Odds API  -> key OK, {len(keys)} sports listed")
    print(f"credits   -> used {used}, remaining {remaining}")
    for sport in ("basketball_nba", "basketball_ncaab", "americanfootball_nfl"):
        print(f"  {sport:22s} {'in season' if sport in keys else 'not currently listed'}")


if __name__ == "__main__":
    main()
