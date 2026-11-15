"""DraftKings salaries from Kyle's manual CSV exports (DKSalaries.csv).

DK's player/salary API blocks scripts, so salaries are self-collected: on a contest's
lineup page, "Export to CSV" saves ``DKSalaries.csv`` (then ``DKSalaries (1).csv``...).
``ingest`` files each export as a gzipped raw copy under ``raw_dir("draftkings")``:

    draftkings/<SPORT>/<YYYY-MM-DD>/<HHMM>et_<type>_<n>g_<hash>.csv.gz

The CSV has no slate id, so a slate is identified by its player IDs: DK's ``ID`` column
is a draftable id, unique to one draft group. Same IDs -> same hash -> same slate, so a
second download of a slate is skipped. Date and start time are the slate's first game
(ET), taken from ``Game Info``.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ET = ZoneInfo("America/New_York")

COLUMNS = ["Position", "Name + ID", "Name", "ID", "Roster Position", "Salary", "Game Info",
           "TeamAbbrev", "AvgPointsPerGame"]
SPORTS = ["NBA", "NFL", "CBB", "CFB", "SOC"]

# "LAL@PHX 11/15/2026 04:00PM ET"; anything else (e.g. "Postponed") has no start time.
_GAME_INFO = re.compile(r"^(\S+)@(\S+) (\d{2}/\d{2}/\d{4} \d{2}:\d{2}[AP]M) ET$")


@dataclass(frozen=True)
class Slate:
    sport: str
    slate_type: str  # "classic", "showdown" or "tiers"
    start_et: datetime  # first game's start
    n_games: int
    key: str  # hash of the player IDs

    def rel_path(self) -> Path:
        name = f"{self.start_et:%H%M}et_{self.slate_type}_{self.n_games}g_{self.key}.csv.gz"
        return Path(self.sport) / f"{self.start_et:%Y-%m-%d}" / name


def read_csv_bytes(data: bytes) -> pd.DataFrame:
    """Parse one export. Checks the header so a wrong file fails loudly."""
    df = pd.read_csv(io.BytesIO(data), encoding="utf-8-sig", dtype={"ID": str})
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"not a DKSalaries export, missing columns: {missing}")
    return df


def _tokens(col: pd.Series) -> set[str]:
    return {t for v in col.dropna() for t in str(v).split("/")}


def detect_sport(df: pd.DataFrame) -> str:
    """Sport from player positions (CBB lists only G and F; CFB has no TE or DST)."""
    pos = _tokens(df["Position"])
    if pos & {"GK", "M", "D"}:
        return "SOC"
    if pos & {"PG", "SG", "SF", "PF", "C"}:
        return "NBA"
    if pos & {"TE", "DST"}:
        return "NFL"
    if pos & {"QB", "RB", "WR"}:
        return "CFB"
    if pos and pos <= {"G", "F"}:
        return "CBB"
    raise ValueError(f"can't tell the sport from positions {sorted(pos)}; pass it explicitly")


def slate_type(df: pd.DataFrame) -> str:
    roster = _tokens(df["Roster Position"])
    if "CPT" in roster:
        return "showdown"
    if any(re.fullmatch(r"T\d+", r) for r in roster):
        return "tiers"
    return "classic"


def game_start_et(info: str) -> datetime | None:
    m = _GAME_INFO.match(str(info).strip())
    if not m:
        return None
    return datetime.strptime(m.group(3), "%m/%d/%Y %I:%M%p").replace(tzinfo=ET)


def describe(df: pd.DataFrame, sport: str | None = None) -> Slate:
    starts = [s for s in map(game_start_et, df["Game Info"]) if s is not None]
    if not starts:
        raise ValueError("no game in Game Info has a start time")
    games = {str(g).split(" ")[0] for g in df["Game Info"] if game_start_et(g)}
    ids = sorted(df["ID"].astype(str))
    key = hashlib.sha1("\n".join(ids).encode()).hexdigest()[:10]
    return Slate(sport or detect_sport(df), slate_type(df), min(starts), len(games), key)


def existing(root: Path, slate: Slate) -> Path | None:
    """A saved copy of this slate, wherever its start time put it."""
    hits = list((root / slate.sport).rglob(f"*_{slate.key}.csv.gz"))
    return hits[0] if hits else None


def ingest(src: Path, root: Path, sport: str | None = None) -> tuple[Slate, Path, bool]:
    """Save one export gzipped under root. Returns (slate, path, saved_now)."""
    data = src.read_bytes()
    slate = describe(read_csv_bytes(data), sport)
    found = existing(root, slate)
    if found:
        return slate, found, False
    dest = root / slate.rel_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    with gzip.open(tmp, "wb") as fh:
        fh.write(data)
    tmp.replace(dest)  # atomic: a crash never leaves a half-written file under the real name
    return slate, dest, True


def load(path: Path) -> pd.DataFrame:
    """One saved slate as a tidy table (one row per player per roster slot)."""
    with gzip.open(path, "rb") as fh:
        df = read_csv_bytes(fh.read())
    sport = path.parts[-3]
    slate = describe(df, sport)
    starts = df["Game Info"].map(game_start_et)
    game = df["Game Info"].astype(str).str.split(" ").str[0]
    return pd.DataFrame({
        "sport": sport,
        "slate_key": slate.key,
        "slate_type": slate.slate_type,
        "draftable_id": df["ID"].astype(str),
        "name": df["Name"],
        "position": df["Position"],
        "roster_position": df["Roster Position"],
        "salary": df["Salary"].astype(int),
        "team": df["TeamAbbrev"],
        "away": game.str.split("@").str[0].where(starts.notna()),
        "home": game.str.split("@").str[1].where(starts.notna()),
        "start_utc": pd.to_datetime([s.astimezone(UTC) if s else None for s in starts],
                                    utc=True),
        "avg_ppg": df["AvgPointsPerGame"].astype(float),
    })


def load_all(root: Path, sports: list[str] | None = None) -> pd.DataFrame:
    paths = sorted(p for p in root.rglob("*.csv.gz") if not sports or p.parts[-3] in sports)
    return pd.concat([load(p) for p in paths], ignore_index=True) if paths else pd.DataFrame()
