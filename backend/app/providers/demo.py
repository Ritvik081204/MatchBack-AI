"""DEMO provider: replays *real* historical matches as if they were in progress.

Nothing here is invented or simulated - every ball comes from Cricsheet. What is simulated is only the
"in progress" position (the replay cut-off), so the experience of joining a match part-way can be demonstrated
without a live feed. Every response is labelled DEMO and never uses the LIVE label.
"""
from __future__ import annotations

from sqlalchemy import select

from .. import models as m
from ..analysis import get_analysis
from ..database import SessionLocal
from ..engine.match_processor import MatchData
from .base import MatchDataProvider
from .historical import HistoricalMatchProvider, _ball_records, match_summary
from .loader import load_match_data

DEMO_LABEL = "DEMO MATCH - a real historical match replayed from a chosen point. This is NOT a live score."
_hist = HistoricalMatchProvider()


def _default_cutoff(md: MatchData) -> int:
    """Pick a mid-match position that makes for a good catch-up (about 55% of the way through the chase / match)."""
    if md.format == "TEST":
        return int(md.max_seq * 0.62)
    inn2 = md.deliveries[md.deliveries.innings_no == 2]
    if len(inn2):
        return int(inn2.seq.iloc[int(len(inn2) * 0.55)])
    return int(md.max_seq * 0.6)


def replay_points(md: MatchData) -> list[dict]:
    """Slider stops: the end of each over, for choosing when the fan 'joins'."""
    pts = []
    for (inn, ov), g in md.deliveries.groupby(["innings_no", "over_no"]):
        if md.format == "TEST" and ov % 5:  # keep payload small: every 5th over for Tests
            continue
        pts.append({"seq": int(g.seq.iloc[-1]), "innings_no": int(inn), "over": int(ov) + 1,
                    "team": g.batting_team.iloc[0], "label": f"Innings {inn} - over {int(ov) + 1}"})
    return pts


class DemoMatchProvider(MatchDataProvider):
    name = "demo"
    data_kind = "DEMO"
    prefix = "demo-"
    label = DEMO_LABEL
    status_word = "DEMO replay"

    def owns(self, match_id: str) -> bool:
        return match_id.startswith(self.prefix)

    def _real(self, match_id: str) -> str:
        return match_id.removeprefix(self.prefix)

    def _cut(self, md: MatchData) -> int:
        return _default_cutoff(md)

    def _demo_ids(self) -> list[str]:
        """One showcase per format/gender, preferring the closest finishes among ingested matches."""
        with SessionLocal() as db:
            rows = db.scalars(select(m.Match).order_by(m.Match.date_start.desc())).all()
        picks: dict[tuple, m.Match] = {}
        for r in rows:
            key = (r.format, r.gender)
            if key not in picks or _closeness(r) < _closeness(picks[key]):
                picks[key] = r
        order = [("ODI", "male"), ("T20", "male"), ("TEST", "male"), ("T20", "female")]
        return [picks[k].id for k in order if k in picks] + [p.id for k, p in picks.items() if k not in order]

    def get_matches(self, *, q=None, fmt=None, gender=None, limit=20, offset=0):  # noqa: ANN001
        items = []
        for mid in self._demo_ids():
            d = self._summary(mid)
            if d and (not fmt or d["format"] == fmt.upper()) and (not gender or d["gender"] == gender.lower()):
                if not q or q.lower() in (d["title"] + (d["tournament"] or "") + (d["venue"] or "")).lower():
                    items.append(d)
        return len(items), items[offset: offset + limit]

    @staticmethod
    def _score_rows(sit: dict, teams: list[dict]) -> list[dict]:
        return [{"innings_no": s["innings_no"], "team": s["team"], "abbr": next(t["abbr"] for t in teams if t["name"] == s["team"]),
                 "score": f"{s['runs']}/{s['wickets']}", "overs": s["overs"], "super_over": False} for s in sit["innings_summary"]]

    def _summary(self, mid: str) -> dict | None:
        with SessionLocal() as db:
            row = db.get(m.Match, mid)
            if not row:
                return None
            md = load_match_data(db, mid)
            base = match_summary(row)
        cut = self._cut(md)
        sit = get_analysis(md, cut).situation
        base.update({
            "id": f"{self.prefix}{mid}", "data_kind": self.data_kind, "status": self.name, "label": self.label,
            "status_text": f"{self.status_word} - {sit['status']}", "default_cutoff": cut,
            "scores": self._score_rows(sit, base["teams"]),
        })
        return base

    def get_match_data(self, match_id: str, cutoff: int | None = None) -> MatchData | None:
        with SessionLocal() as db:
            return load_match_data(db, self._real(match_id))

    def get_match_details(self, match_id: str, cutoff: int | None = None) -> dict | None:
        s = self._summary(self._real(match_id))
        if not s:
            return None
        md = self.get_match_data(match_id)
        cut = s["default_cutoff"] if cutoff is None else max(0, min(cutoff, md.max_seq))
        sit = get_analysis(md, cut).situation
        complete = cut >= md.max_seq
        s.update({
            "cutoff": cut, "situation": sit, "toss": {"winner": md.meta["toss_winner"], "decision": md.meta["toss_decision"]},
            "result": md.result["text"] if complete else None, "winner": md.result["winner"] if complete else None,
            "player_of_match": md.result["player_of_match"] if complete else [],
            "data_issues": md.meta.get("data_issues", []), "squads": md.squads, "balls_per_over": md.balls_per_over,
            "status_text": f"{self.status_word} - {sit['status']}" if not complete else f"{self.status_word} finished - {md.result['text']}",
            "scores": self._score_rows(sit, s["teams"]),
            "replay": {"min_seq": 11, "max_seq": md.max_seq, "default_seq": s["default_cutoff"], "points": replay_points(md)},
        })
        return s

    def get_live_matches(self) -> list[dict]:
        return []  # replays are never reported as live

    def get_scorecard(self, match_id: str, cutoff: int | None = None):
        md = self.get_match_data(match_id)
        return get_analysis(md, cutoff if cutoff is not None else self._cut(md)).scorecard if md else None

    def get_ball_by_ball(self, match_id: str, cutoff: int | None = None):
        md = self.get_match_data(match_id)
        if not md:
            return None
        return _ball_records(md.upto(cutoff if cutoff is not None else self._cut(md)))

    def get_player_statistics(self, player_id: str) -> dict | None:
        return _hist.get_player_statistics(player_id)

    def default_cutoff(self, match_id: str) -> int | None:
        md = self.get_match_data(match_id)
        return self._cut(md) if md else None


def _closeness(r: m.Match) -> float:
    by = (r.outcome or {}).get("by") or {}
    if "runs" in by and "innings" not in by:
        return by["runs"] / (3 if r.format == "T20" else 6 if r.format == "ODI" else 15)
    if "wickets" in by:
        return (by["wickets"] - 1) * 1.5
    return 99
