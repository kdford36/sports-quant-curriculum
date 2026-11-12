from datetime import date

from sportsquant.data.odds_schedule import et_clock, et_date, games_on, start_slots


def ev(commence):
    return {"id": commence, "commence_time": commence}


def test_evening_tipoff_belongs_to_previous_utc_day():
    # 7:10 PM ET on Dec 1 is 00:10 UTC on Dec 2.
    assert et_date("2024-12-02T00:10:00Z") == date(2024, 12, 1)
    assert et_date("2024-12-01T20:40:00Z") == date(2024, 12, 1)
    assert et_date("2024-12-02T05:30:00Z") == date(2024, 12, 2)  # 12:30 AM ET


def test_games_on_filters_by_eastern_date_and_sorts():
    events = [ev("2024-12-02T03:10:00Z"), ev("2024-12-01T20:40:00Z"),
              ev("2024-12-04T00:00:00Z")]
    got = [e["commence_time"] for e in games_on(events, date(2024, 12, 1))]
    assert got == ["2024-12-01T20:40:00Z", "2024-12-02T03:10:00Z"]


def test_start_slots_merge_times_within_the_same_minute():
    events = [ev("2024-12-01T21:30:00Z"), ev("2024-12-01T21:30:05Z"),
              ev("2024-12-01T17:00:00Z")]
    assert start_slots(events) == ["2024-12-01T17:00:00Z", "2024-12-01T21:30:00Z"]


def test_start_slots_never_move_past_kickoff():
    # Flooring can only move a snapshot earlier, so no look-ahead.
    assert start_slots([ev("2024-12-01T21:30:59Z")]) == ["2024-12-01T21:30:00Z"]


def test_et_clock_handles_daylight_saving():
    assert et_clock(date(2024, 12, 1), 10) == "2024-12-01T15:00:00Z"  # EST, UTC-5
    assert et_clock(date(2024, 10, 1), 10) == "2024-10-01T14:00:00Z"  # EDT, UTC-4
