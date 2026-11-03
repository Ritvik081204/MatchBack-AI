from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from ..ai.event_explainer import explain_event
from ..ai.insight_generator import player_insights
from ..ai.question_answering import answer_question, suggestions
from ..ai.summary_generator import generate_recap
from ..analysis import Analysis, get_analysis
from ..providers import demo, historical, live, provider_for, provider_status
from ..providers.demo import DemoMatchProvider
from ..schemas import (AskRequest, AskResponse, CatchUpRequest, CatchUpResponse, EventExplanationRequest,
                       EventExplanationResponse, MatchListResponse)
from ..utils import clean

log = logging.getLogger("matchback.api")
router = APIRouter(prefix="/api/matches", tags=["matches"])

NO_LIVE = ("No live matches: no free, documented live-score API is configured. MatchBack AI never shows historical or "
           "simulated scores as live. Try a DEMO match to experience a mid-match catch-up.")


def _analysis(match_id: str, at: int | None) -> tuple[Analysis, dict]:
    prov = provider_for(match_id)
    md = prov.get_match_data(match_id)
    if md is None:
        raise HTTPException(404, f"Match '{match_id}' not found")
    cutoff = None
    if isinstance(prov, DemoMatchProvider):
        cutoff = prov.default_cutoff(match_id) if at is None else max(0, min(at, md.max_seq))
    a = get_analysis(md, cutoff)
    return a, {"data_kind": prov.data_kind, "cutoff": cutoff}


def _page(items: list[dict], total: int, limit: int, offset: int, notice: str | None = None) -> dict:
    return MatchListResponse(total=total, limit=limit, offset=offset, items=clean(items), notice=notice).model_dump()


@router.get("", response_model=MatchListResponse)
def list_matches(category: str = Query("all", pattern="^(all|recent|completed|demo|live|upcoming)$"), q: str | None = None,
                 format: str | None = Query(None, pattern="^(?i)(T20|ODI|TEST)$"), gender: str | None = Query(None, pattern="^(?i)(male|female)$"),
                 limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    if category == "live":
        return _page([], 0, limit, offset, NO_LIVE)
    if category == "upcoming":
        return _page([], 0, limit, offset, "No upcoming fixtures: a fixture feed is not bundled (Cricsheet only covers played matches).")
    if category == "demo":
        total, items = demo.get_matches(q=q, fmt=format, gender=gender, limit=limit, offset=offset)
        return _page(items, total, limit, offset)
    if category == "recent":
        total, items = historical.get_matches(q=q, fmt=format, gender=gender, limit=min(limit, 12), offset=offset)
        return _page(items, min(total, 12), limit, offset)
    total, items = historical.get_matches(q=q, fmt=format, gender=gender, limit=limit, offset=offset)
    return _page(items, total, limit, offset)


@router.get("/live", response_model=MatchListResponse)
def live_matches():
    return _page(live.get_live_matches(), 0, 20, 0, NO_LIVE)


@router.get("/upcoming", response_model=MatchListResponse)
def upcoming_matches():
    return _page([], 0, 20, 0, "No upcoming fixtures: a fixture feed is not bundled (Cricsheet only covers played matches).")


@router.get("/completed", response_model=MatchListResponse)
def completed_matches(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), q: str | None = None):
    total, items = historical.get_matches(q=q, limit=limit, offset=offset)
    return _page(items, total, limit, offset)


@router.get("/providers/status")
def providers():
    return provider_status()


@router.get("/{match_id}")
def match_details(match_id: str, at: int | None = Query(None, ge=0)):
    d = provider_for(match_id).get_match_details(match_id, at)
    if d is None:
        raise HTTPException(404, f"Match '{match_id}' not found")
    return clean(d)


@router.get("/{match_id}/scorecard")
def scorecard(match_id: str, at: int | None = Query(None, ge=0)):
    a, meta = _analysis(match_id, at)
    return clean({**meta, "innings": a.scorecard, "situation": a.situation})


@router.get("/{match_id}/timeline")
def timeline(match_id: str, at: int | None = Query(None, ge=0),
             category: str | None = Query(None, pattern="^(wicket|boundary|milestone|other)$"),
             innings: int | None = Query(None, ge=1, le=6), min_importance: int = Query(0, ge=0, le=100)):
    a, meta = _analysis(match_id, at)
    ev = [e for e in a.timeline if (not category or e["category"] == category) and (not innings or e["innings_no"] == innings)
          and e["importance"] >= min_importance]
    return clean({**meta, "events": ev, "total_events": len(a.timeline),
                  "counts": {c: sum(1 for e in a.timeline if e["category"] == c) for c in ("wicket", "boundary", "milestone", "other")},
                  "overs": a.overs, "turning_points": a.turning_points, "innings": [{"innings_no": i["innings_no"], "team": i["team"]} for i in a.md.innings]})


@router.get("/{match_id}/statistics")
def statistics(match_id: str, at: int | None = Query(None, ge=0)):
    a, meta = _analysis(match_id, at)
    ins = player_insights(a)
    return clean({**meta, **ins, "partnerships": a.partnerships, "overs": a.overs, "phases": a.phases,
                  "format": a.md.format, "balls_per_over": a.md.balls_per_over})


@router.get("/{match_id}/milestones")
def milestones(match_id: str, at: int | None = Query(None, ge=0), include_superseded: bool = False):
    from ..engine.milestone_detector import UNAVAILABLE
    a, meta = _analysis(match_id, at)
    ms = [m for m in a.milestones if include_superseded or not m["superseded"]]
    return clean({**meta, "milestones": ms, "unavailable": UNAVAILABLE, "total": len(a.milestones)})


@router.get("/{match_id}/turning-points")
def turning_points(match_id: str, at: int | None = Query(None, ge=0)):
    from ..engine.turning_points import CONFIG
    a, meta = _analysis(match_id, at)
    cfg = CONFIG[a.md.format]
    return clean({**meta, "turning_points": a.turning_points, "momentum": a.momentum, "innings": [{"innings_no": i["innings_no"], "team": i["team"]} for i in a.md.innings],
                  "config": cfg.__dict__,
                  "disclaimer": "Momentum is a derived statistical indicator of recent scoring vs the innings trend and wickets lost. "
                                "It is not a validated win-probability model."})


@router.get("/{match_id}/ball-by-ball")
def ball_by_ball(match_id: str, at: int | None = Query(None, ge=0), limit: int = Query(120, ge=1, le=500), offset: int = Query(0, ge=0)):
    prov = provider_for(match_id)
    cutoff = (prov.default_cutoff(match_id) if at is None else at) if isinstance(prov, DemoMatchProvider) else None
    rows = prov.get_ball_by_ball(match_id, cutoff)
    if rows is None:
        raise HTTPException(404, f"Match '{match_id}' not found")
    return clean({"total": len(rows), "limit": limit, "offset": offset, "items": rows[offset: offset + limit]})


@router.get("/{match_id}/suggestions")
def question_suggestions(match_id: str, at: int | None = Query(None, ge=0)):
    a, _ = _analysis(match_id, at)
    return {"suggestions": suggestions(a)[:8]}


@router.post("/{match_id}/catch-up", response_model=CatchUpResponse)
def catch_up(match_id: str, body: CatchUpRequest):
    a, _ = _analysis(match_id, body.at)
    return generate_recap(a, body.length, body.focus, body.use_llm)


@router.post("/{match_id}/ask", response_model=AskResponse)
def ask(match_id: str, body: AskRequest):
    a, _ = _analysis(match_id, body.at)
    return clean(answer_question(a, body.question, body.use_llm))


@router.post("/{match_id}/event-explanation", response_model=EventExplanationResponse)
def event_explanation(match_id: str, body: EventExplanationRequest):
    a, _ = _analysis(match_id, body.at)
    res = explain_event(a, body.event_id, body.use_llm)
    if res is None:
        raise HTTPException(404, f"Event '{body.event_id}' not found at this position in the match")
    return clean(res)
