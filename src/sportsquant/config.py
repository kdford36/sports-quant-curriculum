"""Machine-specific paths and keys, read from the environment (.env).

Every machine has its own .env, so the same code finds the right folders on a
Windows desktop, a laptop or anywhere else without edits.

- DATA_DIR: raw data pulls. Point it at a cloud-synced folder so paid API pulls
  happen once and every machine sees them. Defaults to <repo>/data.
- DB_PATH: the local DuckDB file. Rebuilt from DATA_DIR on each machine, so it
  stays out of the synced folder. Defaults to <repo>/data/local/sportsquant.duckdb.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(REPO_ROOT / ".env")


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name, "").strip()
    return Path(value).expanduser() if value else default


def data_dir() -> Path:
    """Root folder for raw data. Created if missing."""
    path = _path_from_env("DATA_DIR", REPO_ROOT / "data")
    path.mkdir(parents=True, exist_ok=True)
    return path


def raw_dir(source: str) -> Path:
    """Folder for one source's raw pulls, e.g. raw_dir("odds_api")."""
    path = data_dir() / "raw" / source
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    """Local DuckDB file. Its parent folder is created if missing."""
    path = _path_from_env("DB_PATH", REPO_ROOT / "data" / "local" / "sportsquant.duckdb")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def odds_api_key() -> str:
    """The Odds API key. Raises a clear error if this machine has none set."""
    key = os.getenv("ODDS_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "ODDS_API_KEY is not set. Copy .env.example to .env on this machine and add the key."
        )
    return key
