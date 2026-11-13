# Progress

## Current position

- **Phase:** 0 (Code literacy), not started
- **Next lesson:** 0-01, NumPy arrays and broadcasting
- **Week 1 starts:** 2026-11-16
- **Next mock interview:** end of week 2 (2026-11-29)

## Odds API plan

- **Active plan:** 5M ($119/month), bought 2026-11-12.
- **Renews:** about 2026-12-12. Downgrade to the 20K plan ($30) before then, once the backfill is verified.
- **Backfill status:** core plan approved 2026-11-12 (exact plan from game lists: 18,185 calls, est 1,007,720). NBA game lines approved and pulled the same day (second table). Not approved: `us_dfs` props.

  | Step | Calls | Est | Spent (headers) | Errors | Status |
  |---|---|---|---|---|---|
  | Test pull 2024-12-01 | 23 | 1,780 | 1,780 | 0 | done |
  | Game lists (all sports, 10 AM ET daily) | 2,952 | 2,952 | 2,952 | 0 | done |
  | NBA props, 2023 playoffs to 2026-11-11 | 8,338 | 416,900 | 413,880 | 8 | done |
  | CBB lines (us+eu), 2020-21 to 2026-11-11 | 8,976 | 538,560 | 538,380 | 3 | done |
  | NFL lines (us+eu), 2020-21 to 2026-11-11 | 871 | 52,260 | 52,260 | 0 | done |
  | Retry of failed calls | 11 | 580 | 230 | 7 | done |
  | **Total** | **21,171** | **1,013,032** | **1,009,482** | **7** | **done 2026-11-12** |

  The headers show 1,009,485 used: the 3 extra credits are from setup checks before the test pull.

  NBA notes: billing is **per market returned**, not requested (39 calls cost 0, 11 cost 10-40; no props posted yet at 10 AM for some games). 7 calls got 404 (event id gone, likely rescheduled games) and 1 got a 502; a rerun retries only those 8.
  CBB notes: every lines call cost exactly 60 (all markets always returned). 3 calls got a 502 (transient server error).
  Retry: all 4 calls that got a 502 succeeded (230 credits). The 7 NBA 404s failed again and cost 0; they are permanent gaps (event ids the API no longer serves at those times), so those 7 props snapshots are missing. Raw files: `raw/odds_api` under `DATA_DIR`; logs `_credit_log.jsonl`, `_batch_log.jsonl`, `backfill_*.log`.
  NBA game lines (us+eu, one closing snapshot per start-time slot, product `lines`):

  | Step | Calls | Est | Spent (headers) | Errors | Status |
  |---|---|---|---|---|---|
  | NBA game lists 2020-07-22 to 2023-05-02 | 810 | 810 | 810 | 0 | done |
  | NBA lines, 2019-20 bubble to 2026-11-11 | 5,523 | 331,380 | 331,320 | 1 (502) | done |
  | Retry of the 502 | 1 | 60 | 60 | 0 | done |
  | **Total** | **6,334** | **332,250** | **332,190** | **0** | **done 2026-11-12** |

  Every lines call cost exactly 60. No NBA lines gaps.

  NFL props (us, 10 markets: pass yds/TDs/attempts/completions/INTs, rush yds/attempts, receptions, rec yds, anytime TD). Two snapshots per game: 10 AM ET the **day before** (early price) and kickoff (closing). Props history starts 2023-05-03, so 2023-24 is the first season (checked: the API returns a 422 for Super Bowl LVII props, at no cost).

  | Step | Calls | Est (max) | Spent (headers) | Errors | Status |
  |---|---|---|---|---|---|
  | Test pull, Sunday 2024-12-01 | 22 | 2,200 | 2,200 | 0 | done |
  | NFL props, 2023-24 to 2026-11-11 | 1,960 | 196,000 | 193,560 | 1 (404) | done |
  | **Total** | **1,982** | **198,200** | **195,760** | **1** | **done 2026-11-12** |

  1,915 calls cost the full 100; 66 cost less (some markets not posted yet at the day-before snapshot). The 404 failed again on retry: the early snapshot of Rams @ Lions (2024-01-14 wild card) is missing; its closing snapshot is on disk.
  The 2025-01-05 NFL game list repeats 12 games (same id and time); the props planner now plans each game once per season.
- **Credits used so far:** 1,537,435 of 5,000,000; remaining 3,462,565 (2026-11-12, all approved pulls complete).

## Open items

- [x] Odds API backfill: NBA props, CBB and NFL lines pulled through 2026-11-11 (2026-11-12). 7 NBA props snapshots permanently missing (404).
- [x] NBA game lines pulled, 2019-20 bubble through 2026-11-11 (2026-11-12).
- [x] NFL props pulled, 2023-24 through 2026-11-11 (2026-11-12). 1 early snapshot missing (404).
- [ ] Optional before 2026-12-12: `us_dfs` props with the spare credits. Needs a cost estimate and Kyle's yes first.
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
