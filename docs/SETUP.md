# Working across machines

Git carries the code, notebooks, proofs, quizzes and `PROGRESS.md`. A cloud-synced folder carries the raw data. Each machine keeps its own `.env` and its own DuckDB file.

| What | Where it lives | How it moves between machines |
| --- | --- | --- |
| Code, notebooks, proofs, quizzes, PROGRESS.md | Git repo | `git pull` / `git push` |
| Python environment | `.venv` (per machine) | Rebuilt from `uv.lock` by `uv sync` |
| Raw data pulls (paid API responses) | `DATA_DIR` in a synced folder | Google Drive for desktop / OneDrive sync |
| DuckDB database | `DB_PATH` (per machine, not synced) | Rebuilt from raw files |
| API keys | `.env` (per machine, never committed) | Typed once per machine |

## First time on a new machine

1. Install Git, VS Code and Claude Code.
2. Install Google Drive for desktop (or OneDrive) and make sure the `sports-quant-data` folder is syncing.
3. Clone and set up:

   ```
   git clone https://github.com/kdford36/sports-quant-curriculum.git
   cd sports-quant-curriculum
   ```

   Windows: `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`
   Mac/Linux: `bash scripts/setup.sh`

   This installs `uv`, builds `.venv` with Python 3.13 from the lock file, turns on notebook output stripping, creates `.env` and runs the tests.

4. Edit `.env`: paste `ODDS_API_KEY` and set `DATA_DIR` to the synced folder's path on this machine.
5. Open the folder in VS Code and pick the `.venv` interpreter.

## Every session

1. **Start:** `git pull`. Claude Code does this first (see CLAUDE.md).
2. Work the lesson.
3. **End:** commit and push, even if the lesson is half done (`wip:` commits are fine). Claude Code does this at close.

Never leave a machine with uncommitted work: the next machine will not see it, and two diverging copies of a notebook are painful to merge.

## Why notebook outputs are stripped

Notebook outputs (tables, charts, timestamps) change every run, so two machines running the same notebook create conflicting files. `nbstripout` removes outputs when you commit; the code and markdown cells stay. Re-run a notebook to see its outputs.

## Adding a dependency

Claude adds it with `uv add <package>` (or `uv add --optional <group> <package>`), which updates `pyproject.toml` and `uv.lock`. Commit both. Other machines pick it up with `uv sync --all-extras` after pulling.

## If a pull conflicts

- `PROGRESS.md` or a markdown file: keep both sides' lines, then commit.
- A notebook: keep the newer machine's version (`git checkout --theirs <file>`), re-run it, commit.
- `uv.lock`: run `uv lock` again, then commit.
