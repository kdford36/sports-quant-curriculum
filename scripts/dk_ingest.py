"""File DraftKings salary exports (DKSalaries*.csv) as raw data.

    uv run python scripts/dk_ingest.py                 # from ~/Downloads
    uv run python scripts/dk_ingest.py --src some/dir  # from another folder
    uv run python scripts/dk_ingest.py --remove        # also delete the originals once saved
    uv run python scripts/dk_ingest.py --sport CBB FILE.csv   # if the sport can't be detected

Each export is saved gzipped under DATA_DIR/raw/draftkings/<SPORT>/<date>/; a slate
already on disk is skipped. See sportsquant.data.dk_salaries.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sportsquant.config import raw_dir
from sportsquant.data.dk_salaries import SPORTS, ingest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", type=Path, help="exports (default: DKSalaries*.csv in --src)")
    ap.add_argument("--src", type=Path, default=Path.home() / "Downloads")
    ap.add_argument("--sport", choices=SPORTS, help="override sport detection")
    ap.add_argument("--remove", action="store_true", help="delete each original once it is saved")
    a = ap.parse_args()

    files = a.files or sorted(a.src.glob("DKSalaries*.csv"))
    if not files:
        print(f"No DKSalaries*.csv in {a.src}")
        return
    root = raw_dir("draftkings")
    saved = skipped = failed = 0
    with open(root / "_ingest_log.jsonl", "a") as log:
        for f in files:
            try:
                slate, dest, new = ingest(f, root, a.sport)
            except ValueError as e:
                failed += 1
                print(f"  FAILED  {f.name}: {e}")
                continue
            saved += new
            skipped += not new
            status = "saved  " if new else "on disk"
            print(f"  {status} {f.name:28} {slate.sport:4} {slate.start_et:%Y-%m-%d %H:%M} ET "
                  f"{slate.slate_type:9} {slate.n_games:2} games -> {dest.relative_to(root)}")
            if new:
                log.write(json.dumps({"at": datetime.now(UTC).isoformat(), "file": f.name,
                                      "path": str(dest.relative_to(root)),
                                      "sport": slate.sport, "type": slate.slate_type,
                                      "games": slate.n_games}) + "\n")
            if a.remove:
                f.unlink()
    print(f"{saved} saved, {skipped} already on disk, {failed} failed")


if __name__ == "__main__":
    main()
