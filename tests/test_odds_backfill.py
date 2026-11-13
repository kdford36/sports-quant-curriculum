from datetime import date

from sportsquant.data.odds_backfill import Batch, batches, calls_for_day


def ev(id_, commence):
    return {"id": id_, "commence_time": commence}


def test_nba_two_props_calls_per_game_morning_and_tip():
    events = [ev("a", "2024-12-01T20:40:00Z"), ev("b", "2024-12-02T00:10:00Z"),
              ev("later", "2024-12-04T00:00:00Z")]
    calls = calls_for_day("basketball_nba", "props", date(2024, 12, 1), events)
    assert [c.args[1:3] for c in calls] == [
        ("a", "2024-12-01T15:00:00Z"), ("a", "2024-12-01T20:40:00Z"),
        ("b", "2024-12-01T15:00:00Z"), ("b", "2024-12-02T00:10:00Z"),
    ]
    assert all(c.expected == 50 for c in calls)


def test_no_props_before_coverage_starts():
    assert calls_for_day("basketball_nba", "props", date(2023, 5, 2),
                         [ev("a", "2023-05-02T23:00:00Z")]) == []


def test_lines_one_call_per_slot():
    events = [ev("a", "2024-12-01T18:00:00Z"), ev("b", "2024-12-01T18:00:00Z"),
              ev("c", "2024-12-01T21:25:00Z")]
    calls = calls_for_day("americanfootball_nfl", "lines", date(2024, 12, 1), events)
    assert [c.args[1] for c in calls] == ["2024-12-01T18:00:00Z", "2024-12-01T21:25:00Z"]
    assert all(c.expected == 60 for c in calls)


def test_batches_stop_at_yesterday_and_skip_future_seasons():
    got = batches(date(2026, 11, 11), ["americanfootball_nfl"])
    assert got[-1] == Batch("americanfootball_nfl", "lines", date(2026, 9, 1), date(2026, 11, 11))
    assert len(got) == 7
    assert got[0].name == "americanfootball_nfl lines 2020-21"
    assert batches(date(2026, 8, 1), ["americanfootball_nfl"])[-1].end == date(2026, 2, 15)


def test_spring_window_is_labeled_with_the_season_it_finishes():
    nba = batches(date(2026, 11, 11), ["basketball_nba"], ["props"])
    assert [b.name for b in nba[:2]] == ["basketball_nba props 2022-23",
                                         "basketball_nba props 2023-24"]


def test_nba_lines_start_with_the_2020_bubble_and_are_one_call_per_slot():
    lines = batches(date(2026, 11, 11), ["basketball_nba"], ["lines"])
    assert [b.name for b in lines[:2]] == ["basketball_nba lines 2019-20",
                                           "basketball_nba lines 2020-21"]
    assert lines[-1].start == date(2026, 10, 1)
    events = [ev("a", "2024-12-02T00:00:00Z"), ev("b", "2024-12-02T00:00:30Z"),
              ev("c", "2024-12-02T03:00:00Z")]
    calls = calls_for_day("basketball_nba", "lines", date(2024, 12, 1), events)
    assert [(c.kind, c.args[1], c.expected) for c in calls] == [
        ("odds", "2024-12-02T00:00:00Z", 60), ("odds", "2024-12-02T03:00:00Z", 60)]
