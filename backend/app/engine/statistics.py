"""Scorecards, bowling figures, partnerships, over-by-over data and per-player aggregates.

Cricket rules applied (see tests/):
* batter runs exclude every extra; wides are not balls faced, no-balls are
* bowler runs = batter runs + wides + no-balls (byes, leg-byes and penalties are not charged)
* only legal deliveries (no wide / no-ball) count towards overs
* run-outs, retirements, timed-out, obstructing, handled-ball and hit-twice never credit the bowler
* a maiden is a complete over of legal balls with zero bowler runs
"""
from __future__ import annotations

import pandas as pd

from .match_processor import MatchData, overs_str, rate

# Highlight thresholds, in legal balls, so single-ball cameos cannot "win" strike rate / economy.
MIN_BALLS_STRIKE_RATE = {"T20": 12, "ODI": 20, "TEST": 30}
MIN_BALLS_ECONOMY = {"T20": 12, "ODI": 30, "TEST": 60}

# Transparent, custom contribution weights (not any platform's official fantasy scoring).
IMPACT_WEIGHTS = {
    "run": 1.0, "four": 1.0, "six": 2.0, "fifty": 8, "hundred": 16, "duck": -2,
    "wicket": 25, "maiden": 6, "three_w": 8, "five_w": 16, "catch": 8, "stumping": 12, "run_out": 10,
}


def _pct(a: float, b: float) -> float | None:
    return round(a * 100 / b, 2) if b else None


def dismissal_text(kind: str, bowler: str, fielders: list[str]) -> str:
    f = " / ".join(fielders) if fielders else ""
    return {
        "bowled": f"b {bowler}",
        "lbw": f"lbw b {bowler}",
        "caught": f"c {f or 'sub'} b {bowler}",
        "caught and bowled": f"c & b {bowler}",
        "stumped": f"st {f or 'wk'} b {bowler}",
        "hit wicket": f"hit wicket b {bowler}",
        "run out": f"run out ({f})" if f else "run out",
    }.get(kind, kind)


def batting_card(md: MatchData, n: int) -> dict:
    d = md.innings_df(n)
    meta = md.innings_meta(n)
    order: list[str] = []
    for b, ns in zip(d.batter, d.non_striker):
        for p in (b, ns):
            if p and p not in order:
                order.append(p)
    agg = d.groupby("batter").agg(runs=("batter_runs", "sum"), balls=("faced", "sum"),
                                  fours=("is_four", "sum"), sixes=("is_six", "sum"))
    wk = md.wickets[md.wickets.innings_no == n]
    rows = []
    for pos, name in enumerate(order, start=1):
        a = agg.loc[name] if name in agg.index else None
        runs = int(a.runs) if a is not None else 0
        balls = int(a.balls) if a is not None else 0
        out = wk[wk.player_out == name]
        row = {
            "position": pos, "name": name, "runs": runs, "balls": balls,
            "fours": int(a.fours) if a is not None else 0, "sixes": int(a.sixes) if a is not None else 0,
            "strike_rate": _pct(runs, balls), "out": False, "dismissal": "not out", "dismissed_seq": None,
        }
        if len(out):
            w = out.iloc[-1]
            if w.kind not in ("retired hurt", "retired not out"):
                row.update(out=True, dismissal=dismissal_text(w.kind, w.bowler, list(w.fielders)), dismissed_seq=int(w.seq))
            else:
                row.update(dismissal=w.kind)
        rows.append(row)
    st_extras = {k: int(d[k].sum()) for k in ("wides", "noballs", "byes", "legbyes", "penalty")}
    runs = int(d.total.sum())
    wkts = int(d.n_wickets.sum())
    balls = int(d.legal.sum())
    yet = []
    if md.squads.get(meta["team"]):
        yet = [p for p in md.squads[meta["team"]] if p not in order]
    return {
        "innings_no": n, "team": meta["team"], "batters": rows, "yet_to_bat": yet,
        "extras": {"total": int(d.extras.sum()), **st_extras},
        "total": {"runs": runs, "wickets": wkts, "overs": overs_str(balls, md.balls_per_over),
                  "legal_balls": balls, "run_rate": rate(runs, balls, md.balls_per_over)},
        "declared": bool(meta.get("declared")), "finished": md.innings_finished(n),
        "fall_of_wickets": fall_of_wickets(md, n),
    }


def fall_of_wickets(md: MatchData, n: int) -> list[dict]:
    wk = md.wickets[(md.wickets.innings_no == n) & md.wickets.team_wicket]
    d = md.deliveries.set_index("seq")
    out = []
    for w in wk.itertuples():
        r = d.loc[w.seq]
        out.append({"wicket_no": int(w.wicket_no), "player": w.player_out, "runs": int(r.team_runs),
                    "over": f"{r.over_no}.{r.ball_no}", "seq": int(w.seq)})
    return out


def bowling_card(md: MatchData, n: int) -> dict:
    d = md.innings_df(n)
    bpo = md.balls_per_over
    wk = md.wickets[(md.wickets.innings_no == n) & md.wickets.bowler_credited]
    wk_by = wk.groupby("bowler").size()
    over_b = d.groupby(["over_no", "bowler"]).agg(legal=("legal", "sum"), br=("bowler_runs", "sum")).reset_index()
    maidens = over_b[(over_b.legal == bpo) & (over_b.br == 0)].groupby("bowler").size()
    rows = []
    for name in dict.fromkeys(d.bowler):
        b = d[d.bowler == name]
        balls = int(b.legal.sum())
        runs = int(b.bowler_runs.sum())
        wkts = int(wk_by.get(name, 0))
        rows.append({
            "name": name, "overs": overs_str(balls, bpo), "legal_balls": balls,
            "maidens": int(maidens.get(name, 0)), "runs": runs, "wickets": wkts,
            "economy": rate(runs, balls, bpo), "average": round(runs / wkts, 2) if wkts else None,
            "strike_rate": round(balls / wkts, 1) if wkts else None,
            "dots": int(((b.bowler_runs == 0) & b.legal).sum()),
            "wides": int(b.wides.sum()), "noballs": int(b.noballs.sum()),
        })
    return {"innings_no": n, "team": next(t for t in md.teams if t != md.innings_meta(n)["team"]), "bowlers": rows}


def scorecard(md: MatchData) -> list[dict]:
    out = []
    for i in md.innings:
        n = i["innings_no"]
        out.append({**batting_card(md, n), "bowling": bowling_card(md, n)["bowlers"],
                    "target_runs": i.get("target_runs"), "super_over": bool(i.get("super_over"))})
    return out


# ---------------------------------------------------------------------------
def over_by_over(md: MatchData) -> list[dict]:
    d = md.deliveries
    bpo = md.balls_per_over
    rows = []
    for (inn, ov), g in d.groupby(["innings_no", "over_no"], sort=True):
        last = g.iloc[-1]
        legal = int(g.legal.sum())
        rows.append({
            "innings_no": int(inn), "team": last.batting_team, "over": int(ov) + 1, "runs": int(g.total.sum()),
            "wickets": int(g.n_wickets.sum()), "legal_balls": legal, "complete": legal >= bpo,
            "boundaries": int(g.is_four.sum() + g.is_six.sum()), "fours": int(g.is_four.sum()), "sixes": int(g.is_six.sum()),
            "extras": int(g.extras.sum()), "bowlers": list(dict.fromkeys(g.bowler)),
            "maiden": bool(legal >= bpo and g.bowler_runs.sum() == 0 and g.bowler.nunique() == 1),
            "cum_runs": int(last.team_runs), "cum_wickets": int(last.team_wkts),
            "run_rate": rate(int(last.team_runs), int(last.legal_balls), bpo),
            "start_seq": int(g.seq.iloc[0]), "end_seq": int(g.seq.iloc[-1]),
        })
    return rows


PARTNERSHIP_STEPS = (50, 100, 150, 200, 250, 300)


def partnerships(md: MatchData) -> list[dict]:
    """Segment each innings at every wicket (team wicket or retirement); report runs incl. extras."""
    out = []
    for i in md.innings:
        n = i["innings_no"]
        d = md.innings_df(n)
        seg = _new_seg(0, 0)
        wicket_count = 0
        rows = list(d.itertuples())
        for idx, r in enumerate(rows):
            if seg["start_seq"] is None:
                seg["start_seq"] = int(r.seq)
                seg["start_label"] = f"{r.over_no}.{r.ball_no}"
            prev = seg["runs"]
            seg["runs"] += int(r.total)
            seg["balls"] += int(r.legal)
            for p in (r.batter, r.non_striker):
                if p and p not in seg["batters"]:
                    seg["batters"][p] = {"runs": 0, "balls": 0}
            seg["batters"][r.batter]["runs"] += int(r.batter_runs)
            seg["batters"][r.batter]["balls"] += int(r.faced)
            for step in PARTNERSHIP_STEPS:
                if prev < step <= seg["runs"]:
                    seg["steps"].append({"step": step, "seq": int(r.seq), "label": f"{r.over_no}.{r.ball_no}"})
            seg["end_seq"] = int(r.seq)
            seg["end_label"] = f"{r.over_no}.{r.ball_no}"
            if r.is_wicket:
                w = md.wickets[md.wickets.seq == r.seq].iloc[0]
                seg.update(ended_by=f"{w.player_out} ({w.kind})", unbroken=False)
                out.append(_finish_seg(seg, n, i["team"], wicket_count + 1))
                wicket_count += int(r.n_wickets)
                seg = _new_seg(0, 0)
        if seg["start_seq"] is not None:  # open / unbroken partnership
            seg.update(ended_by=None, unbroken=True)
            out.append(_finish_seg(seg, n, i["team"], wicket_count + 1))
    return out


def _new_seg(a: int, b: int) -> dict:
    return {"runs": a, "balls": b, "batters": {}, "steps": [], "start_seq": None, "end_seq": None, "unbroken": False}


def _finish_seg(seg: dict, n: int, team: str, wicket_no: int) -> dict:
    names = list(seg["batters"])[:2]
    return {
        "innings_no": n, "team": team, "wicket_no": wicket_no, "batters": names,
        "contributions": {k: v for k, v in seg["batters"].items()},
        "runs": seg["runs"], "balls": seg["balls"], "start_seq": seg["start_seq"], "end_seq": seg["end_seq"],
        "start_over": seg["start_label"], "end_over": seg["end_label"], "unbroken": seg["unbroken"],
        "ended_by": seg.get("ended_by"), "steps": seg["steps"], "run_rate": rate(seg["runs"], seg["balls"], 6),
    }


# ---------------------------------------------------------------------------
def player_stats(md: MatchData) -> list[dict]:
    """Aggregate every player's match performance across all innings."""
    stats: dict[str, dict] = {}

    def get(name: str) -> dict:
        if name not in stats:
            stats[name] = {
                "name": name, "team": md.player_team(name), "batting": None, "bowling": None,
                "fielding": {"catches": 0, "run_outs": 0, "stumpings": 0}, "innings_detail": [],
            }
        return stats[name]

    for i in md.innings:
        n = i["innings_no"]
        for b in batting_card(md, n)["batters"]:
            s = get(b["name"])
            bt = s["batting"] or {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "innings": 0, "dismissals": 0,
                                  "fifties": 0, "hundreds": 0, "ducks": 0, "high_score": 0}
            bt["runs"] += b["runs"]; bt["balls"] += b["balls"]; bt["fours"] += b["fours"]; bt["sixes"] += b["sixes"]
            bt["innings"] += 1; bt["dismissals"] += int(b["out"])
            bt["fifties"] += int(50 <= b["runs"] < 100); bt["hundreds"] += int(b["runs"] >= 100)
            bt["ducks"] += int(b["out"] and b["runs"] == 0)
            bt["high_score"] = max(bt["high_score"], b["runs"])
            s["batting"] = bt
            s["innings_detail"].append({"innings_no": n, "kind": "bat", "runs": b["runs"], "balls": b["balls"], "out": b["out"]})
        for b in bowling_card(md, n)["bowlers"]:
            s = get(b["name"])
            bw = s["bowling"] or {"legal_balls": 0, "runs": 0, "wickets": 0, "maidens": 0, "dots": 0,
                                  "three_w": 0, "five_w": 0, "best": None}
            bw["legal_balls"] += b["legal_balls"]; bw["runs"] += b["runs"]; bw["wickets"] += b["wickets"]
            bw["maidens"] += b["maidens"]; bw["dots"] += b["dots"]
            bw["three_w"] += int(b["wickets"] >= 3); bw["five_w"] += int(b["wickets"] >= 5)
            if bw["best"] is None or (b["wickets"], -b["runs"]) > (bw["best"]["wickets"], -bw["best"]["runs"]):
                bw["best"] = {"wickets": b["wickets"], "runs": b["runs"], "innings_no": n}
            s["bowling"] = bw
            s["innings_detail"].append({"innings_no": n, "kind": "bowl", "wickets": b["wickets"], "runs": b["runs"]})

    for w in md.wickets.itertuples():
        for f in w.fielders:
            fs = get(f)["fielding"]
            if w.kind == "caught":
                fs["catches"] += 1
            elif w.kind == "stumped":
                fs["stumpings"] += 1
            elif w.kind == "run out":
                fs["run_outs"] += 1
        if w.kind == "caught and bowled":
            get(w.bowler)["fielding"]["catches"] += 1

    out = []
    bpo = md.balls_per_over
    for s in stats.values():
        bt, bw, fl = s["batting"], s["bowling"], s["fielding"]
        if bt:
            bt["strike_rate"] = _pct(bt["runs"], bt["balls"])
            bt["average"] = round(bt["runs"] / bt["dismissals"], 2) if bt["dismissals"] else None
        if bw:
            bw["overs"] = overs_str(bw["legal_balls"], bpo)
            bw["economy"] = rate(bw["runs"], bw["legal_balls"], bpo)
            bw["average"] = round(bw["runs"] / bw["wickets"], 2) if bw["wickets"] else None
        s["impact"] = round(_impact(bt, bw, fl), 1)
        did_bat = bool(bt and bt["balls"] > 0)
        did_bowl = bool(bw and bw["legal_balls"] > 0)
        s["observed_role"] = ("All-rounder" if did_bat and did_bowl and bt["balls"] >= 6 and bw["legal_balls"] >= bpo
                              else "Bowler" if did_bowl and not (did_bat and bt["runs"] >= 20) else "Batter" if did_bat else "Fielder")
        s["is_player_of_match"] = s["name"] in md.result.get("player_of_match", []) if md.complete else False
        out.append(s)
    out.sort(key=lambda x: -x["impact"])
    return out


def _impact(bt: dict | None, bw: dict | None, fl: dict) -> float:
    W = IMPACT_WEIGHTS
    pts = 0.0
    if bt:
        pts += bt["runs"] * W["run"] + bt["fours"] * W["four"] + bt["sixes"] * W["six"]
        pts += bt["fifties"] * W["fifty"] + bt["hundreds"] * W["hundred"] + bt["ducks"] * W["duck"]
    if bw:
        pts += bw["wickets"] * W["wicket"] + bw["maidens"] * W["maiden"] + bw["three_w"] * W["three_w"] + bw["five_w"] * W["five_w"]
    pts += fl["catches"] * W["catch"] + fl["stumpings"] * W["stumping"] + fl["run_outs"] * W["run_out"]
    return pts


def highlights(md: MatchData, stats: list[dict]) -> dict:
    fmt = md.format
    bats = [s for s in stats if s["batting"] and s["batting"]["balls"] > 0]
    bowls = [s for s in stats if s["bowling"] and s["bowling"]["legal_balls"] > 0]
    res: dict = {"top_scorer": None, "top_wicket_taker": None, "best_strike_rate": None, "best_economy": None,
                 "most_impactful": None, "all_round": None}
    if bats:
        s = max(bats, key=lambda x: (x["batting"]["runs"], -x["batting"]["balls"]))
        res["top_scorer"] = {"name": s["name"], "team": s["team"], "runs": s["batting"]["runs"], "balls": s["batting"]["balls"]}
    wk = [s for s in bowls if s["bowling"]["wickets"] > 0]
    if wk:
        s = max(wk, key=lambda x: (x["bowling"]["wickets"], -x["bowling"]["runs"]))
        res["top_wicket_taker"] = {"name": s["name"], "team": s["team"], "wickets": s["bowling"]["wickets"], "runs": s["bowling"]["runs"]}
    sr = [s for s in bats if s["batting"]["balls"] >= MIN_BALLS_STRIKE_RATE[fmt]]
    if sr:
        s = max(sr, key=lambda x: x["batting"]["strike_rate"])
        res["best_strike_rate"] = {"name": s["name"], "team": s["team"], "strike_rate": s["batting"]["strike_rate"],
                                   "runs": s["batting"]["runs"], "balls": s["batting"]["balls"],
                                   "min_balls": MIN_BALLS_STRIKE_RATE[fmt]}
    eco = [s for s in bowls if s["bowling"]["legal_balls"] >= MIN_BALLS_ECONOMY[fmt]]
    if eco:
        s = min(eco, key=lambda x: x["bowling"]["economy"])
        res["best_economy"] = {"name": s["name"], "team": s["team"], "economy": s["bowling"]["economy"],
                               "overs": s["bowling"]["overs"], "min_balls": MIN_BALLS_ECONOMY[fmt]}
    if stats:
        s = stats[0]
        res["most_impactful"] = {"name": s["name"], "team": s["team"], "impact": s["impact"]}
    both = [s for s in stats if s["batting"] and s["bowling"] and s["batting"]["runs"] > 0 and s["bowling"]["wickets"] > 0]
    if both:
        s = max(both, key=lambda x: x["impact"])
        res["all_round"] = {"name": s["name"], "team": s["team"], "runs": s["batting"]["runs"],
                            "wickets": s["bowling"]["wickets"], "impact": s["impact"]}
    return res


def phases(md: MatchData, n: int) -> list[dict]:
    """Format-aware innings phases (T20: powerplay/middle/death, ODI: 1-10/11-40/41-50). Tests have none."""
    if md.format == "TEST":
        return []
    bpo = md.balls_per_over
    limit = md.overs_limit or (20 if md.format == "T20" else 50)
    cuts = [6, 15, limit] if md.format == "T20" else [10, 40, limit]
    names = ["Powerplay", "Middle overs", "Death overs"]
    d = md.innings_df(n)
    res, lo = [], 0
    for name, hi in zip(names, cuts):
        g = d[(d.over_no >= lo) & (d.over_no < hi)]
        if len(g):
            balls = int(g.legal.sum())
            res.append({"name": name, "from_over": lo + 1, "to_over": min(hi, int(g.over_no.max()) + 1),
                        "runs": int(g.total.sum()), "wickets": int(g.n_wickets.sum()),
                        "run_rate": rate(int(g.total.sum()), balls, bpo), "complete": balls >= (hi - lo) * bpo})
        lo = hi
    return res
