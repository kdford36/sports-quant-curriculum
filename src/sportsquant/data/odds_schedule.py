"""Which snapshots to pull for a given game day.

Two rules learned from the first event lists (2024-12-01):

- A game's *day* is its US Eastern date. Slicing the UTC string puts every
  7 PM ET tip-off on the next day (7:10 PM ET = 00:10Z), which halved the NBA slate.
- Game-line snapshots are taken per *start-time slot*: one sport-wide snapshot at a
  start time holds the closing line for every game starting then. Start times that
  differ only by seconds resolve to the same 5-minute snapshot, so they are merged
  to the minute (rounding down, which never moves a snapshot past kickoff).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def parse_utc(ts: str) -> datetime:
    """'2024-12-01T20:40:00Z' -> aware UTC datetime."""
    return datetime.fromisoformat(ts).astimezone(UTC)


def to_iso_z(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def et_date(commence_time: str) -> date:
    """The game day as US Eastern date."""
    return parse_utc(commence_time).astimezone(ET).date()


def games_on(events: list[dict], day: date) -> list[dict]:
    """Events whose Eastern-time date is ``day``, sorted by start time."""
    return sorted((e for e in events if et_date(e["commence_time"]) == day),
                  key=lambda e: e["commence_time"])


def start_slots(events: list[dict]) -> list[str]:
    """Distinct start times, floored to the minute, as ISO 'Z' strings."""
    floored = {parse_utc(e["commence_time"]).replace(second=0, microsecond=0) for e in events}
    return [to_iso_z(t) for t in sorted(floored)]


def et_clock(day: date, hour: int, minute: int = 0) -> str:
    """A wall-clock time on ``day`` in Eastern time, as ISO 'Z' (handles EST/EDT)."""
    return to_iso_z(datetime.combine(day, time(hour, minute), tzinfo=ET))
