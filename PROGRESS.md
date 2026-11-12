# Progress

## Current position

- **Phase:** 0 (Code literacy), not started
- **Next lesson:** 0-01, NumPy arrays and broadcasting
- **Week 1 starts:** 2026-11-16
- **Next mock interview:** end of week 2 (2026-11-29)

## Odds API plan

- **Active plan:** 5M ($119/month), bought 2026-11-12.
- **Renews:** about 2026-12-12. Downgrade to the 20K plan ($30) before then, once the backfill is verified.
- **Backfill status:** client built and tested; one-day test pull done (2024-12-01). Estimate 1,780 credits, headers 1,780. Full-backfill estimate (~1.16M) waiting for Kyle's yes.
- **Credits used so far:** 1,783 of 5,000,000 (2026-11-12).

## Open items

- [ ] Odds API backfill: approve the full-backfill estimate, then pull history in batches. See docs/KICKOFF.md (session A) and docs/DATA.md.
- [ ] Downgrade The Odds API to the 20K plan before 2026-12-12.
- [x] Windows desktop: repo at `C:\Users\kford\dev\sports-quant-curriculum`, `DATA_DIR` local at `C:\Users\kford\dev\sports-quant-data` (not synced; copy it to any other machine before pulling there).
- [x] docs/SETUP.md and CLAUDE.md updated: `DATA_DIR` is a local folder, not a synced one.
- [ ] Order anchor texts: Blitzstein & Hwang first (Phase 1), Axler next (Phase 2).

## Weak spots to resurface

From the Odds API code walkthrough (2026-11-12):
- Short-circuit `and` with a `None` guard (`x is not None and x - y < z`): the right side never runs when the left is False.
- Atomic writes (write to `.tmp`, then rename) and why a half-written cache file is worse than none.
- UTC vs. local game day: slicing a UTC timestamp's date puts evening ET games on the next day.
- Cached vs. live calls: a cached call sends no request at all, so it has no credit header.

## Lesson log

| Date | Lesson | Quiz score | Notes |
| --- | --- | --- | --- |

## Mock interviews

| Date | Score | Main misses |
| --- | --- | --- |

## Proofs

| Phase | Proof | Status |
| --- | --- | --- |
