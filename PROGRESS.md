# Progress

## Current position

- **Phase:** 0 (Code literacy), not started
- **Next lesson:** 0-01, NumPy arrays and broadcasting
- **Week 1 starts:** 2026-11-16
- **Next mock interview:** end of week 2 (2026-11-29)

## Odds API plan

- **Active plan:** 5M ($119/month), bought 2026-11-12.
- **Renews:** about 2026-12-12. Downgrade to the 20K plan ($30) before then, once the backfill is verified.
- **Backfill status:** core plan approved 2026-11-12 (exact plan from game lists: 18,185 calls, est 1,007,720). Not approved: `us_dfs` props, NBA game lines.

  | Step | Calls | Est | Spent (headers) | Errors | Status |
  |---|---|---|---|---|---|
  | Test pull 2024-12-01 | 23 | 1,780 | 1,780 | 0 | done |
  | Game lists (all sports, 10 AM ET daily) | 2,952 | 2,952 | 2,952 | 0 | done |
  | NBA props, 2023 playoffs to 2026-11-11 | 8,338 | 416,900 | 413,880 | 8 | done |
  | CBB lines (us+eu), 2020-21 to now | 9,076 | 538,560 | | | next |
  | NFL lines (us+eu), 2020 to now | 871 | 52,260 | | | |

  NBA notes: billing is **per market returned**, not requested (39 calls cost 0, 11 cost 10-40; no props posted yet at 10 AM for some games). 7 calls got 404 (event id gone, likely rescheduled games) and 1 got a 502; a rerun retries only those 8.
- **Credits used so far:** 418,615 of 5,000,000; remaining 4,581,385 (2026-11-12, after NBA).

## Open items

- [ ] Odds API backfill: NBA done; CBB, then NFL, then one rerun to retry the 8 failed NBA calls. See docs/KICKOFF.md (session A) and docs/DATA.md.
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
