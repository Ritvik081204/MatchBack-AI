from __future__ import annotations

from sqlalchemy import func, or_, select

from .. import models as m
from ..database import SessionLocal
from ..engine.match_processor import MatchData, overs_str
from ..analysis import get_analysis
from .base import MatchDataProvider
from .loader import load_match_data


def team_ref(t: m.Team) -> dict:
    return {"name": t.name, "abbr": t.abbreviation}


def match_summary(row: m.Match) -> dict:
    """Card-level summary built from stored innings totals (no delivery loading)."""
    scores = []
    for i in row.innings:
        scores.append({"innings_no": i.innings_no, "team": i.team.name, "abbr": i.team.abbreviation,
                       "score": f"{i.total_runs}/{i.wickets}", "overs": overs_str(i.legal_balls, row.balls_per_over),
                       "super_over": i.super_over})
    return {
        "id": row.id, "title": f"{row.team1.name} vs {row.team2.name}", "teams": [team_ref(row.team1), team_ref(row.team2)],
        "format": row.format, "gender": row.gender, "tournament": row.tournament, "stage": row.stage, "season": row.season,
        "venue": row.venue, "city": row.city, "date": row.date_start, "date_end": row.date_end, "data_kind": "HISTORICAL",
        "status": "completed", "status_text": row.outcome_text, "scores": scores,
        "label": "HISTORICAL - completed match (Cricsheet ball-by-ball data)",
    }


class HistoricalMatchProvider(MatchDataProvider):
    name = "historical"
    data_kind = "HISTORICAL"

    def owns(self, match_id: str) -> bool:
        return not match_id.startswith("demo-")

    def get_matches(self, *, q=None, fmt=None, gender=None, limit=20, offset=0):  # noqa: ANN001
        with SessionLocal() as db:
            stmt = select(m.Match)
            if fmt:
                stmt = stmt.where(m.Match.format == fmt.upper())
            if gender:
                stmt = stmt.where(m.Match.gender == gender.lower())
            if q:
                like = f"%{q.lower()}%"
                t1, t2 = m.Team.__table__.alias("t1"), m.Team.__table__.alias("t2")
                stmt = stmt.join(t1, m.Match.team1_id == t1.c.id).join(t2, m.Match.team2_id == t2.c.id).where(or_(
                    func.lower(t1.c.name).like(like), func.lower(t2.c.name).like(like), func.lower(m.Match.venue).like(like),
                    func.lower(m.Match.tournament).like(like), func.lower(m.Match.city).like(like)))
            total = db.scalar(select(func.count()).select_from(stmt.subquery()))
            rows = db.scalars(stmt.order_by(m.Match.date_start.desc(), m.Match.id.desc()).limit(limit).offset(offset)).unique().all()
            return total or 0, [match_summary(r) for r in rows]

    def get_match_data(self, match_id: str, cutoff: int | None = None) -> MatchData | None:
        with SessionLocal() as db:
            return load_match_data(db, match_id)  # historical matches are always complete

    def get_match_details(self, match_id: str, cutoff: int | None = None) -> dict | None:
        with SessionLocal() as db:
            row = db.get(m.Match, match_id)
            if not row:
                return None
            md = load_match_data(db, match_id)
            a = get_analysis(md, None)
            return {**match_summary(row), "toss": {"winner": row.toss_winner, "decision": row.toss_decision},
                    "situation": a.situation, "result": row.outcome_text, "winner": row.winner,
                    "player_of_match": row.player_of_match, "data_issues": row.data_issues, "cutoff": None,
                    "squads": row.squads, "balls_per_over": row.balls_per_over, "replay": None}

    def get_live_matches(self) -> list[dict]:
        return []  # historical data is never presented as live

    def get_scorecard(self, match_id: str, cutoff: int | None = None):
        md = self.get_match_data(match_id)
        return get_analysis(md, None).scorecard if md else None

    def get_ball_by_ball(self, match_id: str, cutoff: int | None = None):
        md = self.get_match_data(match_id)
        return _ball_records(md) if md else None

    def get_player_statistics(self, player_id: str) -> dict | None:
        with SessionLocal() as db:
            try:
                pid = int(player_id)
            except ValueError:
                return None
            p = db.get(m.Player, pid)
            if not p:
                return None
            rows = db.execute(select(m.PlayerMatchStatistics, m.Match).join(m.Match, m.Match.id == m.PlayerMatchStatistics.match_id)
                              .where(m.PlayerMatchStatistics.player_id == pid).order_by(m.Match.date_start.desc())).all()
            agg = {"matches": len(rows), "runs": 0, "balls_faced": 0, "fours": 0, "sixes": 0, "wickets": 0, "balls_bowled": 0,
                   "runs_conceded": 0, "catches": 0, "run_outs": 0, "stumpings": 0, "impact": 0.0}
            history = []
            for s, mt in rows:
                for k in list(agg)[1:]:
                    agg[k] += getattr(s, k)
                history.append({"match_id": mt.id, "title": f"{mt.team1.name} vs {mt.team2.name}", "date": mt.date_start,
                                "format": mt.format, "team": s.team, "runs": s.runs, "balls": s.balls_faced, "wickets": s.wickets,
                                "runs_conceded": s.runs_conceded, "impact": s.impact})
            agg["strike_rate"] = round(agg["runs"] * 100 / agg["balls_faced"], 2) if agg["balls_faced"] else None
            agg["economy"] = round(agg["runs_conceded"] * 6 / agg["balls_bowled"], 2) if agg["balls_bowled"] else None
            agg["impact"] = round(agg["impact"], 1)
            return {"id": p.id, "name": p.name, "cricsheet_id": p.cricsheet_id,
                    "scope_note": "Totals cover only the matches ingested into this MatchBack AI database - not career statistics.",
                    "totals": agg, "matches": history}


def _ball_records(md: MatchData) -> list[dict]:
    d = md.deliveries
    cols = ["seq", "innings_no", "batting_team", "over_no", "ball_no", "label", "batter", "non_striker", "bowler", "batter_runs",
            "extras", "total", "legal", "is_wicket", "is_four", "is_six", "team_runs", "team_wkts"]
    return d[cols].to_dict("records")
