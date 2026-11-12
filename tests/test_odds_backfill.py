from datetime import date

from sportsquant.data.odds_backfill import Batch, batches, calls_for_day


def ev(id_, commence):
    return {"id": id_, "commence_time": commence}


def test_nba_two_props_calls_per_game_morning_and_tip():
    events = [ev("a", "2024-12-01T20:40:00Z"), ev("b", "2024-12-02T00:10:00Z"),
              ev("later", "2024-12-04T00:00:00Z")]
    calls = calls_for_day("basketball_nba", date(2024, 12, 1), events)
    assert [c.args[1:3] for c in calls] == [
        ("a", "2024-12-01T15:00:00Z"), ("a", "2024-12-01T20:40:00Z"),
        ("b", "2024-12-01T15:00:00Z"), ("b", "2024-12-02T00:10:00Z"),
    ]
    assert all(c.expected == 50 for c in calls)


def test_no_props_before_coverage_starts():
    assert calls_for_day("basketball_nba", date(2023, 5, 2),
                         [ev("a", "2023-05-02T23:00:00Z")]) == []


def test_lines_one_call_per_slot():
    events = [ev("a", "2024-12-01T18:00:00Z"), ev("b", "2024-12-01T18:00:00Z"),
              ev("c", "2024-12-01T21:25:00Z")]
    calls = calls_for_day("americanfootball_nfl", date(2024, 12, 1), events)
    assert [c.args[1] for c in calls] == ["2024-12-01T18:00:00Z", "2024-12-01T21:25:00Z"]
    assert all(c.expected == 60 for c in calls)


def test_batches_stop_at_yesterday_and_skip_future_seasons():
    got = batches(date(2026, 11, 11), ["americanfootball_nfl"])
    assert got[-1] == Batch("americanfootball_nfl", date(2026, 9, 1), date(2026, 11, 11))
    assert len(got) == 7
    assert got[0].name == "americanfootball_nfl 2020-21"
    assert batches(date(2026, 8, 1), ["americanfootball_nfl"])[-1].end == date(2026, 2, 15)


def test_spring_window_is_labeled_with_the_season_it_finishes():
    nba = batches(date(2026, 11, 11), ["basketball_nba"])
    assert [b.name for b in nba[:2]] == ["basketball_nba 2022-23", "basketball_nba 2023-24"]
