# Data sources and odds plan

Decided 2026-11-12. Budget: about $100/month, shared with the portfolio.

## Decision: The Odds API, one heavy month then a cheap plan

Buy **one month of the 5M plan ($119)** in late November to backfill history, then drop to the **20K plan ($30/month)** to keep collecting current odds going forward. Averaged over a year that is roughly $37/month.

Why The Odds API:

- Historical NBA player props back to **May 3, 2023**, at 5-minute snapshots; game lines (moneyline, spread, total) back to **June 2020**. Historical data is on every paid plan.
- Covers NBA, NFL and college basketball, US books (DraftKings, FanDuel, BetMGM, Caesars...), **Pinnacle** in the `eu` region as a sharp reference for game lines, and DFS pick'em sites in the `us_dfs` region.
- Already used in the MLB betting pipeline.

Plans (from the-odds-api.com, checked 2026-11-12):

| Plan | Price | Credits/month |
| --- | --- | --- |
| Starter | Free | 500 (no historical) |
| 20K | $30 | 20,000 |
| 100K | $59 | 100,000 |
| 5M | $119 | 5,000,000 |
| 15M | $249 | 15,000,000 |

## Credit math for the backfill

Historical calls cost **10 × markets × regions** credits. Player props are pulled one game at a time (historical event-odds endpoint); game lines come back for a whole sport per snapshot.

| Pull | Calculation | Credits (approx.) |
| --- | --- | --- |
| NBA props, 2023-24 to 2025-26 | ~3,900 games × 2 snapshots (morning, near tip) × 10 × 5 markets × 1 region | ~390,000 |
| NBA props, add `us_dfs` region | doubles the line above | +390,000 |
| CBB lines, 2020-21 to 2025-26 | ~10,800 snapshots × 10 × 3 markets × 2 regions (us + eu/Pinnacle) | ~650,000 |
| NFL lines, 2020 to 2025 | ~660 snapshots × 10 × 3 × 2 | ~40,000 |
| **Total** | | **~1.5M of 5M** |

These are estimates. Before the full pull, run one day's worth and read the `x-requests-used` / `x-requests-remaining` response headers to confirm the real cost per call.

Markets for NBA props: `player_points`, `player_rebounds`, `player_assists`, `player_threes`, `player_points_rebounds_assists`.

## Free sources

| Need | Source |
| --- | --- |
| NBA box scores, play-by-play | `nba_api` |
| NFL play-by-play, schedules (schedules also carry closing spread and total) | nflverse via `nflreadpy` |
| CBB games and team stats | public CBB packages and sites, chosen in Phase 2 |
| DFS salaries | self-collected slate CSVs to start |

## Alternatives considered

| Provider | Why not now |
| --- | --- |
| SportsGameOdds | Historical data only on the Pro plan ($299/month); the $99 Rookie plan has none. |
| OddsPapi | Free tier (250 requests/month) claims historical odds including Pinnacle, capped at 3 books per call. Too small for a backfill, but worth a free key later as a Pinnacle cross-check. Claims are from the vendor's own blog. |
| OddsJam, OpticOdds | Sales-call enterprise pricing, far over budget. |

## Storage rule

Every raw response is saved as-is (JSON, gzipped) under `DATA_DIR/raw/odds_api/` before any parsing, so a paid pull never has to be repeated. Parsed tables are rebuilt into the local DuckDB from those files.
