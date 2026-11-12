# Sports Quant Curriculum

A self-directed curriculum in machine learning, applied mathematics and statistics, built around sportsbook and DFS pricing problems on NBA, NFL and college basketball data.

Each lesson pairs a concept (with the math written out) with code built and debugged together in Claude Code. A parallel proof track works through the central results in probability, linear algebra, optimization and inference.

## Capstones

1. **NBA player-prop pricing engine:** count models and hierarchical pooling produce fair lines, compared against market prices.
2. **DFS lineup optimizer and contest simulator (NBA, NFL):** integer programming with correlation-aware simulation.
3. **CBB and NFL side/total model:** ratings, calibration and Kelly sizing, backtested against closing lines.

## Layout

```
lessons/           one notebook per lesson
src/sportsquant/   reusable code (odds, de-vig, ratings, optimizer, simulation)
tests/             pytest suite
proofs/            proofs in Markdown + LaTeX
quizzes/           lesson quizzes and scores
interviews/        mock-interview scorecards
docs/              setup and data notes
```

## Setup

See [docs/SETUP.md](docs/SETUP.md). Short version: clone, then run `scripts/setup.ps1` (Windows) or `scripts/setup.sh` (Mac/Linux).
