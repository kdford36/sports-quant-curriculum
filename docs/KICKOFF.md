# Kickoff: first Claude Code sessions

Claude Code reads `CLAUDE.md` automatically when you open it in this repo, so these prompts stay short. Paste one per session.

## Before the first session (once per machine)

1. Clone and run setup (see `docs/SETUP.md`).
2. Open `.env` and fill in `ODDS_API_KEY` and `DATA_DIR`. Type the key into the file yourself; never paste it into a chat.
3. Open a terminal in the repo folder and run `claude`.

## Session A: Odds API backfill (do this first, this week)

The 5M plan is active now, so the backfill comes before Phase 1 instead of after. Paste:

> We're starting the Odds API backfill (see CLAUDE.md's Odds API section, docs/DATA.md and PROGRESS.md). Treat it as a code-reading session for me: build the client in `src/sportsquant/data/odds_api.py` with tests, walk me through how it saves raw responses, skips files it already has and tracks credits, and have me predict what a call returns before you run it. Then do a one-day test pull: one NBA date with props (us region) and the same date's CBB and NFL game lines (us + eu). Show me the credits the headers report against your estimate. Stop there and give me a full backfill cost estimate before pulling anything else.

After you approve the estimate, the follow-up prompt is simply:

> Approved. Run the backfill in batches, log credits after each batch, and update PROGRESS.md as it goes.

## Session B: Lesson 0-01 (Monday, Nov 16)

> Start lesson 0-01 following the session protocol in CLAUDE.md.

From then on, every session can start with:

> Next lesson.
