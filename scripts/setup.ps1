# One-time setup on a new Windows machine. Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

Write-Host "Creating .venv with Python 3.13 and installing locked dependencies..."
uv sync --all-extras

Write-Host "Stripping notebook outputs on commit (avoids merge conflicts across machines)..."
uv run nbstripout --install --attributes .git/info/attributes

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env from .env.example. Fill in ODDS_API_KEY and DATA_DIR before pulling data."
}

Write-Host "Running tests..."
uv run pytest -q

Write-Host "Done. In VS Code, select the interpreter at .venv\Scripts\python.exe."
