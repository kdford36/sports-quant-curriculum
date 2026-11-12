from pathlib import Path

import pytest

from sportsquant import config


def test_data_dir_defaults_to_repo_data(monkeypatch):
    monkeypatch.delenv("DATA_DIR", raising=False)
    assert config.data_dir() == config.REPO_ROOT / "data"


def test_data_dir_uses_env_and_creates_folder(monkeypatch, tmp_path):
    target = tmp_path / "synced" / "sports-quant-data"
    monkeypatch.setenv("DATA_DIR", str(target))
    assert config.data_dir() == target
    assert target.is_dir()


def test_raw_dir_is_under_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert config.raw_dir("odds_api") == tmp_path / "raw" / "odds_api"


def test_db_path_override(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db" / "x.duckdb"))
    path = config.db_path()
    assert path == tmp_path / "db" / "x.duckdb"
    assert path.parent.is_dir()


def test_missing_odds_key_raises(monkeypatch):
    monkeypatch.setenv("ODDS_API_KEY", "")
    with pytest.raises(RuntimeError, match="ODDS_API_KEY"):
        config.odds_api_key()


def test_blank_env_value_falls_back(monkeypatch):
    monkeypatch.setenv("DATA_DIR", "   ")
    assert config.data_dir() == Path(config.REPO_ROOT / "data")
