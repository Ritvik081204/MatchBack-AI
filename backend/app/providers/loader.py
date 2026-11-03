"""Rebuilds a MatchData from the database (same code path as fresh Cricsheet parses)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from ..engine.match_processor import MatchData, build_match_data

_CACHE: dict[str, MatchData] = {}


def load_match_data(db: Session, match_id: str) -> MatchData | None:
    if match_id in _CACHE:
        return _CACHE[match_id]
    row = db.get(m.Match, match_id)
    if not row:
        return None
    names = {p.id: p.name for p in db.scalars(select(m.Player).where(
        m.Player.id.in_(select(m.Delivery.batter_id).where(m.Delivery.match_id == match_id).union(
            select(m.Delivery.bowler_id).where(m.Delivery.match_id == match_id),
            select(m.Delivery.non_striker_id).where(m.Delivery.match_id == match_id),
            select(m.Wicket.player_out_id).where(m.Wicket.match_id == match_id)))))}
    wk: dict[int, list[dict]] = {}
    for w in db.scalars(select(m.Wicket).where(m.Wicket.match_id == match_id).order_by(m.Wicket.id)):
        wk.setdefault(w.delivery_seq, []).append({"kind": w.kind, "player_out": names[w.player_out_id], "fielders": list(w.fielders or [])})
    deliveries = []
    for d in db.scalars(select(m.Delivery).where(m.Delivery.match_id == match_id).order_by(m.Delivery.seq)):
        deliveries.append({
            "seq": d.seq, "innings_no": d.innings_no, "over_no": d.over_no, "ball_idx": d.ball_idx,
            "batter": names[d.batter_id], "non_striker": names.get(d.non_striker_id), "bowler": names[d.bowler_id],
            "batter_runs": d.batter_runs, "extras": d.extras, "total": d.total, "wides": d.wides, "noballs": d.noballs,
            "byes": d.byes, "legbyes": d.legbyes, "penalty": d.penalty, "non_boundary": d.non_boundary,
            "wickets": wk.get(d.seq, []), "review": d.review,
        })
    innings = [{"innings_no": i.innings_no, "team": i.team.name, "target_runs": i.target_runs, "target_overs": i.target_overs,
                "declared": i.declared, "forfeited": i.forfeited, "super_over": i.super_over} for i in row.innings]
    meta = {
        "tournament": row.tournament, "stage": row.stage, "season": row.season, "venue": row.venue, "city": row.city,
        "gender": row.gender, "date_start": row.date_start, "date_end": row.date_end, "toss_winner": row.toss_winner,
        "toss_decision": row.toss_decision, "outcome_text": row.outcome_text, "player_of_match": row.player_of_match or [],
        "data_issues": row.data_issues or [],
    }
    md = build_match_data(
        match_id=row.id, fmt=row.format, teams=[row.team1.name, row.team2.name], squads=row.squads or {},
        balls_per_over=row.balls_per_over, overs_limit=row.overs_limit, meta=meta, innings=innings,
        deliveries=deliveries, info_outcome=row.outcome,
    )
    _CACHE[match_id] = md
    return md


def clear_cache() -> None:
    _CACHE.clear()
