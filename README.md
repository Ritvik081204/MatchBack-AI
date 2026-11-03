++++++++++++++++++# MatchBack AI

**Missed the match? Catch up in 30 seconds.**

MatchBack AI turns ball-by-ball cricket data into an instant, grounded catch-up for fans who join a match part-way: an AI recap, an interactive timeline, player insights, milestones, ranked turning points, and a Q&A assistant. Everything is free, open source, and works with **no API keys and no LLM installed**.

## The problem
Late joiners must hop between scorecards, commentary and stats pages to learn what they missed. MatchBack AI gives one contextual story, then lets them dig deeper.

## Stack
React + Vite + Tailwind + React Router + Axios + Recharts + Lucide · FastAPI + Pydantic + SQLAlchemy (SQLite, PostgreSQL-compatible) · Pandas/NumPy · Ollama (optional local LLM) · Cricsheet data.

## Architecture
```
Cricsheet JSON -> data_validator -> cricsheet_parser -> MatchData (pandas frames)
   -> statistics | milestone_detector | turning_points | event_detector
   -> Analysis (cached facade) -> context_builder (compact facts)
   -> Ollama LLM (optional, output grounding-checked)  OR  rule-based writer
   -> recap / answers / event explanations
```
- `backend/app/data/` validation, parsing, ingestion pipeline (CLI)
- `backend/app/engine/` all cricket maths (the only place numbers are computed)
- `backend/app/providers/` `MatchDataProvider` interface; `Historical`, `Demo`, and an inert `OptionalLive` provider. A new live source only needs to implement the interface and return `MatchData`; no analytics/AI code changes.
- `backend/app/ai/` LLM service, promp++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ts, context builder, summary/Q&A/explainer/insights, fallback writer
- `backend/app/models.py` Matches, Teams, Players, Innings, Deliveries, Wickets, Partnerships, PlayerMatchStatistics, MatchEvents, MatchMilestones, MatchTurningPoints, MatchSummaries
- `frontend/src/pages/match/` the seven workspace tabs (Overview, AI Catch-Up, Timeline, Scorecard, Player Insights, Milestones, Momentum) + floating "Ask MatchBack AI"

## Run locally (Windows / macOS / Linux)
```bash
# backend  (Python 3.11+)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000      # first start auto-imports the 9 bundled sample matches

# frontend (Node 18+), second terminal
cd frontend
npm install
npm run dev                           # http://localhost:5173  (proxies /api to :8000)
```
Tests: `cd backend && pytest` (91 tests: parsing, extras, legal balls, wickets, batting/bowling stats, partnerships, milestones, turning points, T20/ODI/Test, missing data, recap, Q&A, API).

## Load more historical data
```bash
python -m app.data.ingestion --list-downloads
python -m app.data.ingestion --download ipl --limit 25        # latest 25 IPL matches from Cricsheet
python -m app.data.ingestion --dir path/to/cricsheet_jsons --limit 100
python -m app.data.ingestion --files a.json b.json --force
```
Cricsheet JSON v1.x (`innings[].overs[].deliveries[]`) is supported. Malformed files are skipped and reported; missing optional fields (venue, squads, registry) are tolerated and surfaced as "data notes". Check Cricsheet's terms before redistributing data.

## Data labels & demo mode
- **HISTORICAL**: completed match from Cricsheet.
- **DEMO MATCH**: a *real* historical match replayed up to a chosen ball (slider). Nothing after that ball is used anywhere. It is never presented as live.
- **LIVE**: reserved; no free documented live API is configured, so the Live/Upcoming lists are empty with an explanation.

## How the AI works
1. Python computes all facts (scorecards, partnerships, milestones, turning points).
2. `context_builder` sends a compact JSON (a few KB, never raw deliveries; sized by recap length/focus).
3. If Ollama is up, the model narrates; any figure it adds that is not in the facts causes the output to be rejected. Otherwise (or on failure) the deterministic writer produces the recap from the same facts.
4. Factual Q&A (top scorer, counts, dismissals, partnerships...) is computed in Python; the LLM may only rephrase explanatory answers.

### Configure Ollama (optional)
```bash
ollama pull llama3.2:3b      # then start Ollama; MatchBack AI detects it automatically
```
Env vars in `backend/.env.example` (`OLLAMA_MODEL`, `OLLAMA_HOST`, `LLM_ENABLED=false` to force the fallback). The About page shows which engine is active.

## How events are processed
Batter runs exclude extras; wides are not balls faced, no-balls are; bowler runs = bat + wides + no-balls (byes/leg-byes/penalties excluded); only legal balls make overs; run-outs, retirements etc. never credit the bowler; maidens need 6 legal balls with no bowler runs. Turning points are scored 0-100 from measured indicators with per-format configurable thresholds (`TPConfig`) and overlap suppression, so a lone wicket is not a turning point. **Momentum and "advantage" are derived heuristics, not win probabilities.**

## Deploy for free
- **Frontend**: Vercel (root `frontend`, build `npm run build`, output `dist`). Set `VITE_API_URL` to the backend URL.
- **Backend**: Render / Railway / Fly.io free tier: `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`; set `CORS_ORIGINS` to the Vercel URL. SQLite plus bundled samples work out of the box (free-tier disks are ephemeral; samples re-import on start). Ollama is not available on most free hosts, so the rule-based writer is used there.

## Current limitations
- No live feed; demo replays historical matches.
- Career milestones and "fastest ever" claims are intentionally not made (single-match data only; "fastest in this match" is reported).
- Player roles are inferred from play; contribution score is a simple custom weighted sum.
- Legacy Cricsheet formats (pre-1.0 `"1st innings"` layout) are unsupported.
- Q&A is intent-based; unrecognised questions get a clear "not available" answer.
- Team flags/logos are not used (generated abbreviations only).

## Live-stream prototype (/live-demo)
A stream-page mock-up (neutral placeholder in place of the video, optional local video file, score ticker, event pop-ups, 'Just joined? Catch Me Up' banner, and the AI tabs/assistant under the stream). The match data is a real historical match replayed ball by ball and labelled DEMO STREAM.
