"""DK salary export ingest. Synthetic exports in DK's DKSalaries.csv format."""

from __future__ import annotations

from datetime import datetime

import pytest

from sportsquant.data.dk_salaries import (
    ET,
    describe,
    game_start_et,
    ingest,
    load,
    load_all,
    read_csv_bytes,
)

HEADER = "Position,Name + ID,Name,ID,Roster Position,Salary,Game Info,TeamAbbrev,AvgPointsPerGame\n"

NBA_CLASSIC = HEADER + (
    "PG,Luka Doncic (1001),Luka Doncic,1001,PG/G/UTIL,11200,LAL@PHX 11/15/2026 04:00PM ET,LAL,55.1\n"
    "C,Nikola Jokic (1002),Nikola Jokic,1002,C/UTIL,12000,PHX@DEN 11/15/2026 09:00PM ET,DEN,60.3\n"
    "SF/PF,Kevin Durant (1003),Kevin Durant,1003,SF/PF/F/UTIL,9100,LAL@PHX 11/15/2026 04:00PM ET,PHX,44.0\n"
)
NFL_SHOWDOWN = HEADER + (
    "QB,Joe Burrow (2001),Joe Burrow,2001,CPT,16800,PIT@CIN 11/15/2026 08:20PM ET,CIN,22.4\n"
    "QB,Joe Burrow (2002),Joe Burrow,2002,FLEX,11200,PIT@CIN 11/15/2026 08:20PM ET,CIN,22.4\n"
    "DST,Steelers  (2003),Steelers ,2003,FLEX,4000,PIT@CIN 11/15/2026 08:20PM ET,PIT,7.1\n"
)


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8-sig")  # DK exports may carry a BOM
    return p


def test_describe_nba_classic_slate():
    s = describe(read_csv_bytes(NBA_CLASSIC.encode("utf-8-sig")))
    assert (s.sport, s.slate_type, s.n_games) == ("NBA", "classic", 2)
    assert s.start_et == datetime(2026, 11, 15, 16, 0, tzinfo=ET)  # first game, not the last
    assert str(s.rel_path()).replace("\\", "/").startswith("NBA/2026-11-15/1600et_classic_2g_")


def test_showdown_nfl_and_detection_of_other_sports():
    s = describe(read_csv_bytes(NFL_SHOWDOWN.encode()))
    assert (s.sport, s.slate_type, s.n_games) == ("NFL", "showdown", 1)
    cbb = NBA_CLASSIC.replace("PG,", "G,").replace("SF/PF,", "F,").replace("C,Nikola", "F,Nikola")
    assert describe(read_csv_bytes(cbb.encode())).sport == "CBB"
    soc = NFL_SHOWDOWN.replace("QB,", "F,").replace("DST,", "GK,")
    assert describe(read_csv_bytes(soc.encode())).sport == "SOC"


def test_game_info_without_a_start_time_is_ignored():
    assert game_start_et("Postponed") is None
    assert game_start_et("LAL@PHX 11/15/2026 12:30AM ET") == datetime(2026, 11, 15, 0, 30, tzinfo=ET)


def test_ingest_saves_once_and_skips_a_second_download(tmp_path):
    root = tmp_path / "raw"
    first = write(tmp_path, "DKSalaries.csv", NBA_CLASSIC)
    again = write(tmp_path, "DKSalaries (1).csv", NBA_CLASSIC.replace("55.1", "55.4"))
    slate, path, new = ingest(first, root)
    assert new and path.exists() and path.name.endswith(f"_{slate.key}.csv.gz")
    _, path2, new2 = ingest(again, root)  # same player IDs = same slate
    assert not new2 and path2 == path
    assert len(list(root.rglob("*.csv.gz"))) == 1


def test_load_gives_one_row_per_slot_with_utc_starts(tmp_path):
    root = tmp_path / "raw"
    ingest(write(tmp_path, "a.csv", NBA_CLASSIC), root)
    ingest(write(tmp_path, "b.csv", NFL_SHOWDOWN), root)
    df = load_all(root)
    assert len(df) == 6 and set(df["sport"]) == {"NBA", "NFL"}
    burrow = df[df["name"] == "Joe Burrow"].sort_values("salary")
    assert list(burrow["roster_position"]) == ["FLEX", "CPT"]  # CPT costs 1.5x
    assert burrow["salary"].iloc[1] == 1.5 * burrow["salary"].iloc[0]
    luka = df[df["draftable_id"] == "1001"].iloc[0]
    assert str(luka["start_utc"]) == "2026-11-15 21:00:00+00:00"  # 4 PM EST = 21:00 UTC
    assert (luka["away"], luka["home"]) == ("LAL", "PHX")
    assert len(load(next(root.rglob("NBA/*/*.csv.gz")))) == 3


def test_a_wrong_file_fails_loudly(tmp_path):
    with pytest.raises(ValueError, match="missing columns"):
        read_csv_bytes(b"Name,Salary\nX,100\n")
