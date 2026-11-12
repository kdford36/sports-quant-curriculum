#!/usr/bin/env bash
# One-time setup on a new Mac or Linux machine. Run from the repo root:
#   bash scripts/setup.sh
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "Creating .venv with Python 3.13 and installing locked dependencies..."
uv sync --all-extras

echo "Stripping notebook outputs on commit (avoids merge conflicts across machines)..."
uv run nbstripout --install --attributes .git/info/attributes

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example. Fill in ODDS_API_KEY and DATA_DIR before pulling data."
fi

echo "Running tests..."
uv run pytest -q

echo "Done. In VS Code, select the interpreter at .venv/bin/python."
