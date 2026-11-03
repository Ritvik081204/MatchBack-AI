"""Core in-memory model: turns flat delivery records into analysis-ready pandas frames.

`MatchData` is the single object every analytics module (statistics, events,
milestones, turning points, AI context) works on. `MatchData.upto(seq)` returns a
truncated copy, which is how "join the match at over N" replays are produced -
nothing after the cut-off leaks into any calculation.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import pandas as pd

from ..data.cricsheet_parser import NON_TEAM_WICKETS, outcome_text  # noqa: F401

BOWLER_WICKETS = {"bowled", "caught", "lbw", "stumped", "caught and bowled", "hit wicket"}

FORMAT_LABEL = {"T20": "T20", "ODI": "ODI", "TEST": "Test"}


def overs_str(legal_balls: int, bpo: int = 6) -> str:
    """Cricket overs notation: 14 legal balls -> '2.2'."""
    return f"{legal_balls // bpo}.{legal_balls % bpo}"


def overs_float(legal_balls: int, bpo: int = 6) -> float:
    return legal_balls / bpo


def rate(runs: float, legal_balls: int, bpo: int = 6) -> float | None:
    return round(runs * bpo / legal_balls, 2) if legal_balls else None


@dataclass
class MatchData:
    match_id: str
    format: str
    teams: list[str]
    squads: dict[str, list[str]]
    balls_per_over: int
    overs_limit: int | None
    meta: dict
    innings: list[dict]  # innings_no, team, target_runs, target_overs, declared, forfeited, super_over
    deliveries: pd.DataFrame
    wickets: pd.DataFrame
    result: dict = field(default_factory=dict)  # outcome_text, winner, player_of_match
    innings_last_seq: dict[int, int] = field(default_factory=dict)
    max_seq: int = 0
    complete: bool = True  # False when this is a truncated replay

    # ---- slicing -------------------------------------------------------
    def upto(self, seq: int | None) -> "MatchData":
        if seq is None or seq >= self.max_seq:
            return self
        seq = max(0, seq)
        d = self.deliveries[self.deliveries.seq <= seq].reset_index(drop=True)
        w = self.wickets[self.wickets.seq <= seq].reset_index(drop=True)
        used = set(d.innings_no)
        return replace(self, deliveries=d, wickets=w, innings=[i for i in self.innings if i["innings_no"] in used],
                       complete=False)

    @property
    def cutoff_seq(self) -> int:
        return int(self.deliveries.seq.max()) if len(self.deliveries) else -1

    def innings_df(self, n: int) -> pd.DataFrame:
        return self.deliveries[self.deliveries.innings_no == n]

    def innings_meta(self, n: int) -> dict:
        return next(i for i in self.innings if i["innings_no"] == n)

    def innings_finished(self, n: int) -> bool:
        return self.cutoff_seq >= self.innings_last_seq.get(n, 10**9)

    @property
    def title(self) -> str:
        return f"{self.teams[0]} vs {self.teams[1]}"

    def player_team(self, name: str) -> str | None:
        for team, players in self.squads.items():
            if name in players:
                return team
        # fall back to batting/bowling records
        d = self.deliveries
        hit = d[d.batter == name]
        if len(hit):
            return hit.batting_team.iloc[0]
        hit = d[d.bowler == name]
        if len(hit):
            return next((t for t in self.teams if t != hit.batting_team.iloc[0]), None)
        return None

    def all_players(self) -> list[str]:
        names = set(self.deliveries.batter) | set(self.deliveries.bowler) | set(self.deliveries.non_striker.dropna())
        for ps in self.squads.values():
            names |= set(ps)
        return sorted(names)


# ---------------------------------------------------------------------------
# Frame construction
# ---------------------------------------------------------------------------
def build_match_data(*, match_id: str, fmt: str, teams: list[str], squads: dict, balls_per_over: int,
                     overs_limit: int | None, meta: dict, innings: list[dict], deliveries: list[dict],
                     info_outcome: dict | None = None) -> MatchData:
    """`deliveries` use the dict shape produced by cricsheet_parser (names, not ids)."""
    df = pd.DataFrame(deliveries)
    team_of = {i["innings_no"]: i["team"] for i in innings}
    df["batting_team"] = df.innings_no.map(team_of)
    df["legal"] = (df.wides == 0) & (df.noballs == 0)
    df["faced"] = df.wides == 0  # no-balls count as balls faced, wides do not
    df["bowler_runs"] = df.batter_runs + df.wides + df.noballs  # byes/leg-byes/penalty are not the bowler's
    df["is_four"] = (df.batter_runs == 4) & ~df.non_boundary
    df["is_six"] = (df.batter_runs == 6) & ~df.non_boundary
    grp = df.groupby(["innings_no", "over_no"])
    df["ball_no"] = grp.legal.cumsum() - df.legal.astype(int) + 1  # the ball being bowled (1-based, legal count)
    df["label"] = df.over_no.astype(str) + "." + df.ball_no.astype(str)

    # wickets -----------------------------------------------------------
    w_rows = []
    for _, r in df[df.wickets.map(len) > 0].iterrows():
        for w in r["wickets"]:
            w_rows.append({
                "seq": r.seq, "innings_no": r.innings_no, "kind": w["kind"], "player_out": w["player_out"],
                "fielders": w["fielders"], "bowler": r.bowler, "batter": r.batter,
                "bowler_credited": w["kind"] in BOWLER_WICKETS,
                "team_wicket": w["kind"] not in NON_TEAM_WICKETS,
            })
    wk = pd.DataFrame(w_rows, columns=["seq", "innings_no", "kind", "player_out", "fielders", "bowler", "batter",
                                       "bowler_credited", "team_wicket"])
    if len(wk):
        wk["wicket_no"] = wk.groupby("innings_no").team_wicket.cumsum().where(wk.team_wicket, 0).astype(int)
    else:
        wk["wicket_no"] = pd.Series(dtype=int)
    df["n_wickets"] = df.seq.map(wk[wk.team_wicket].groupby("seq").size()).fillna(0).astype(int) if len(wk) else 0
    df["is_wicket"] = df.wickets.map(len) > 0

    df["team_runs"] = df.groupby("innings_no").total.cumsum()
    df["team_wkts"] = df.groupby("innings_no").n_wickets.cumsum()
    df["legal_balls"] = df.groupby("innings_no").legal.cumsum().astype(int)
    df["has_review"] = df.review.map(lambda x: isinstance(x, dict))

    o = info_outcome or {}
    last = df.groupby("innings_no").seq.max().to_dict()
    return MatchData(
        match_id=match_id, format=fmt, teams=teams, squads=squads, balls_per_over=balls_per_over,
        overs_limit=overs_limit, meta=meta, innings=innings, deliveries=df.reset_index(drop=True),
        wickets=wk.reset_index(drop=True),
        result={"text": meta.get("outcome_text", ""), "winner": o.get("winner"),
                "player_of_match": meta.get("player_of_match", [])},
        innings_last_seq={int(k): int(v) for k, v in last.items()}, max_seq=int(df.seq.max()), complete=True,
    )


def from_parsed(pm) -> MatchData:  # noqa: ANN001
    info = pm.info
    dates = info["dates"]
    meta = {
        "tournament": (info.get("event") or {}).get("name"),
        "stage": (info.get("event") or {}).get("stage") if isinstance((info.get("event") or {}).get("stage"), str) else None,
        "match_number": (info.get("event") or {}).get("match_number"),
        "season": str(info.get("season")) if info.get("season") is not None else None,
        "venue": info.get("venue"), "city": info.get("city"), "gender": info.get("gender", "male"),
        "date_start": dates[0], "date_end": dates[-1],
        "toss_winner": (info.get("toss") or {}).get("winner"), "toss_decision": (info.get("toss") or {}).get("decision"),
        "outcome_text": outcome_text(info), "player_of_match": info.get("player_of_match", []),
    }
    return build_match_data(
        match_id=pm.match_id, fmt=pm.format, teams=pm.teams, squads=pm.squads,
        balls_per_over=info.get("balls_per_over", 6), overs_limit=info.get("overs"), meta=meta,
        innings=[vars(i) for i in pm.innings], deliveries=pm.deliveries, info_outcome=info.get("outcome"),
    )


# ---------------------------------------------------------------------------
# Live situation
# ---------------------------------------------------------------------------
def team_totals(md: MatchData) -> dict[str, int]:
    d = md.deliveries
    return d.groupby("batting_team").total.sum().to_dict()


def innings_state(md: MatchData, n: int) -> dict:
    d = md.innings_df(n)
    meta = md.innings_meta(n)
    bpo = md.balls_per_over
    runs = int(d.total.sum())
    wkts = int(d.n_wickets.sum())
    balls = int(d.legal.sum())
    return {
        "innings_no": n, "team": meta["team"], "runs": runs, "wickets": wkts, "legal_balls": balls,
        "overs": overs_str(balls, bpo), "run_rate": rate(runs, balls, bpo),
        "finished": md.innings_finished(n), "declared": bool(meta.get("declared")),
        "extras": int(d.extras.sum()), "target_runs": meta.get("target_runs"),
    }


def _at_crease(d: pd.DataFrame) -> tuple[list[str], str | None]:
    """Batters at the crease after the last recorded ball, and whether a replacement is awaited."""
    if not len(d):
        return [], None
    last = d.iloc[-1]
    pair = [last.batter, last.non_striker]
    out = {w["player_out"] for ws in d[d.seq == last.seq].wickets for w in ws}
    present = [p for p in pair if p and p not in out]
    note = "new batter walking in" if len(present) < 2 and out else None
    return present, note


def situation(md: MatchData) -> dict:
    """Current-state snapshot for the match as it stands at the cut-off."""
    d = md.deliveries
    bpo = md.balls_per_over
    last_n = int(d.innings_no.iloc[-1])
    st = innings_state(md, last_n)
    team = st["team"]
    opp = next(t for t in md.teams if t != team)
    limit_overs = md.overs_limit
    sit: dict = {
        "innings_no": last_n, "batting_team": team, "bowling_team": opp, "score": f"{st['runs']}/{st['wickets']}",
        "runs": st["runs"], "wickets": st["wickets"], "overs": st["overs"], "legal_balls": st["legal_balls"],
        "run_rate": st["run_rate"], "innings_finished": st["finished"], "target": None, "required_rate": None,
        "runs_needed": None, "balls_remaining": None, "lead": None, "advantage": None, "projected": None,
        "status": "", "completed": md.complete and md.innings_finished(last_n) and last_n == len(md.innings_last_seq),
        "innings_summary": [innings_state(md, i["innings_no"]) for i in md.innings],
    }
    batters, note = _at_crease(d[d.innings_no == last_n])
    sit["current_batters"] = [] if st["finished"] else batters
    sit["batter_note"] = None if st["finished"] else note
    sit["current_bowler"] = None if st["finished"] else str(d.iloc[-1].bowler)
    sit["last_ball"] = _describe_ball(d.iloc[-1])

    fmt = md.format
    meta = md.innings_meta(last_n)
    if fmt in ("T20", "ODI"):
        target = meta.get("target_runs")
        if target is None and last_n == 2 and not meta.get("super_over"):
            target = innings_state(md, 1)["runs"] + 1
        total_overs = meta.get("target_overs") or limit_overs
        if target and last_n >= 2:
            need = target - st["runs"]
            rem = int(total_overs * bpo - st["legal_balls"]) if total_overs else None
            sit.update(target=int(target), runs_needed=max(need, 0), balls_remaining=rem)
            if rem and need > 0:
                sit["required_rate"] = round(need * bpo / rem, 2) if rem > 0 else None
            sit["advantage"] = _chase_indicator(st, need, rem, sit["required_rate"], bpo)
            if md.complete and st["finished"]:
                sit["status"] = md.result["text"]
            elif need <= 0:
                sit["status"] = f"{team} have reached the target"
            else:
                sit["status"] = f"{team} need {need} from {rem} balls" if rem is not None else f"{team} need {need} runs"
        else:
            if total_overs and st["legal_balls"] >= 12 and not st["finished"]:
                sit["projected"] = round(st["runs"] * total_overs * bpo / st["legal_balls"])
            sit["status"] = ("Innings break" if st["finished"] and not md.complete else
                             md.result["text"] if md.complete and st["finished"] else f"{team} batting (innings {last_n})")
            if st["finished"] and md.complete and last_n == 1:
                sit["status"] = "Innings break"
    else:  # Test
        totals = {t: 0 for t in md.teams}
        counts = {t: 0 for t in md.teams}
        for i in md.innings:
            ist = innings_state(md, i["innings_no"])
            totals[i["team"]] += ist["runs"]
            counts[i["team"]] += 1
        lead = totals[team] - totals[opp]
        sit["lead"] = lead
        chasing = counts[opp] == 2 and counts[team] == 2 and last_n >= 4
        if chasing:
            need = totals[opp] - totals[team] + 1
            sit.update(target=totals[opp] - (totals[team] - st["runs"]) + 1, runs_needed=max(need, 0))
        if md.complete and st["finished"] and last_n == len(md.innings_last_seq):
            sit["status"] = md.result["text"]
        elif chasing:
            sit["status"] = f"{team} need {max(need, 0)} more to win" if need > 0 else f"{team} have reached the target"
        else:
            sit["status"] = (f"{team} lead by {lead}" if lead > 0 else f"{team} trail by {-lead}" if lead < 0
                             else "Scores level") + f" (innings {last_n}{' - closed' if st['finished'] else ''})"
    if not sit["status"]:
        sit["status"] = f"{team} batting"
    return sit


def _chase_indicator(st: dict, need: int, rem: int | None, rrr: float | None, bpo: int) -> dict | None:
    """Heuristic pressure indicator for a chase. NOT a win probability."""
    if need <= 0:
        return {"leader": st["team"], "label": "Target reached", "basis": "runs required <= 0"}
    if rem is None or rem <= 0:
        return None
    if st["legal_balls"] < 12:
        return {"leader": None, "label": "Too early to call", "basis": "fewer than 2 overs bowled"}
    crr = st["run_rate"] or 0
    gap = (rrr or 0) - crr
    wk = st["wickets"]
    if wk >= 9 or (rrr or 0) > 18:
        leader, label = "bowling", "Bowling side firmly ahead"
    elif gap <= -1.5 and wk <= 6:
        leader, label = "batting", "Batting side ahead"
    elif gap >= 1.5 or wk >= 7:
        leader, label = "bowling", "Bowling side ahead"
    else:
        leader, label = None, "Evenly poised"
    return {"leader": leader, "label": label, "gap_rpo": round(gap, 2), "wickets_lost": wk,
            "basis": "required rate vs current rate and wickets lost (heuristic, not a win probability)"}


def _describe_ball(r) -> str:  # noqa: ANN001
    if r.is_wicket:
        return f"WICKET to {r.bowler}"
    if r.wides:
        return f"wide ({r.total} run{'s' if r.total != 1 else ''})"
    if r.noballs:
        return f"no-ball ({r.total})"
    if r.is_six:
        return "SIX"
    if r.is_four:
        return "FOUR"
    return f"{r.total} run{'s' if r.total != 1 else ''}" if r.total else "dot ball"
