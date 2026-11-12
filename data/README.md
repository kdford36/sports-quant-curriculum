# data/

Nothing in this folder is committed except this file.

- **Raw pulls** go to `DATA_DIR/raw/<source>/` (see `.env`). Point `DATA_DIR` at a cloud-synced folder so paid API pulls happen once and every machine sees them.
- **The DuckDB file** lives at `DB_PATH` (default `data/local/sportsquant.duckdb`). It is local to each machine and rebuilt from the raw files, never synced.

If `DATA_DIR` is blank, raw pulls land here in `data/raw/`, which only that machine will have.
