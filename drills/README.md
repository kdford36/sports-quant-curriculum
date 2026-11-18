# drills/

Short timed coding exercises, separate from lessons. One folder per drill: `D-001_<slug>/` with `prompt.md` (the task), `solution.py` (Kyle's code, typed from a blank file) and `test_drill.py` (Claude's tests, shown after the attempt).

Rules:

- Timer on. Blank file. No AI suggestions, no copying from earlier drills or lessons. Official library docs are fine.
- Run `uv run pytest drills/D-001_<slug>` when done.
- A drill that needed hints comes back in 3 days, then 1 week, until it is clean.
- Log each attempt in `PROGRESS.md` under "Drill log".

Types: Python and data handling (most days), SQL in DuckDB, algorithms (interview-style), probability in code.
