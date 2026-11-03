"""Statistical turning-point detection.

Rules are configurable (TPConfig per format). Each rule emits candidates with a 0-100 score computed from
measurable quantities (wickets in a window, run-rate gaps, partnership size...). Candidates are ranked and
overlapping ones are suppressed so a single passage of play is reported once. A lone wicket is NOT a turning
point unless it ends a large partnership.

These are derived statistical indicators, not win probabilities.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .match_processor import MatchData, rate
from .statistics import over_by_over, partnerships


@dataclass(frozen=True)
class TPConfig:
    cluster_balls: int      # window (legal balls) in which wickets must fall
    cluster_min_wkts: int
    big_partnership: int    # runs
    high_over_runs: int
    shift_overs: int        # rolling window (overs) for acceleration / slowdown
    shift_ratio_up: float
    shift_ratio_down: float
    shift_min_delta: float  # min change in runs/over between consecutive windows
    spell_min_overs: int
    spell_econ_ratio: float # spell economy must be <= ratio * innings run rate
    consecutive_boundaries: int
    chase_swing_rpo: float  # change in required rate over 3 overs
    max_points: int
    min_score: float = 40.0


CONFIG = {
    "T20": TPConfig(18, 2, 40, 15, 3, 1.5, 0.6, 3.0, 2, 0.7, 3, 2.5, 6),
    "ODI": TPConfig(36, 3, 60, 13, 5, 1.4, 0.6, 2.0, 3, 0.7, 3, 2.0, 8),
    "TEST": TPConfig(90, 3, 100, 12, 12, 1.5, 0.5, 1.0, 4, 0.6, 3, 99.0, 10),
}

KIND_LABEL = {
    "collapse": "Collapse after a strong stand", "wicket_cluster": "Cluster of wickets",
    "partnership_broken": "Big partnership broken", "high_scoring_over": "Expensive over",
    "acceleration": "Scoring acceleration", "slowdown": "Scoring slowdown", "restrictive_spell": "Tight bowling spell",
    "boundary_burst": "Boundary burst", "pressure_rise": "Chase pressure rises", "pressure_ease": "Chase pressure eases",
}


def _lbl(r) -> str:  # noqa: ANN001
    return f"{r.over_no}.{r.ball_no}"


def _window(d: pd.DataFrame, a: int, b: int) -> dict:
    g = d[(d.seq >= a) & (d.seq <= b)]
    balls = int(g.legal.sum())
    return {"runs": int(g.total.sum()), "wickets": int(g.n_wickets.sum()), "balls": balls,
            "run_rate": rate(int(g.total.sum()), balls)}


def detect_turning_points(md: MatchData, cfg: TPConfig | None = None) -> list[dict]:
    cfg = cfg or CONFIG[md.format]
    cands: list[dict] = []
    parts = partnerships(md)
    overs = over_by_over(md)
    for i in md.innings:
        n = i["innings_no"]
        d = md.innings_df(n).reset_index(drop=True)
        if len(d) < 12:
            continue
        team = i["team"]
        cands += _wicket_rules(md, d, n, team, cfg, [p for p in parts if p["innings_no"] == n])
        cands += _over_rules(md, d, n, team, cfg, [o for o in overs if o["innings_no"] == n])
        cands += _spell_rules(md, d, n, team, cfg)
        cands += _boundary_rules(d, n, team, cfg)
        cands += _chase_rules(md, d, n, team, cfg)

    cands = [c for c in cands if c["score"] >= cfg.min_score]
    cands.sort(key=lambda c: -c["score"])
    chosen: list[dict] = []
    for c in cands:
        if any(c["innings_no"] == k["innings_no"] and c["start_seq"] <= k["end_seq"] + 6 and k["start_seq"] <= c["end_seq"] + 6
               for k in chosen):
            continue
        chosen.append(c)
        if len(chosen) >= cfg.max_points:
            break
    for rank, c in enumerate(chosen, start=1):
        c["rank"] = rank
        c["id"] = f"tp-{c['start_seq']}-{c['kind']}"
        c["label"] = KIND_LABEL[c["kind"]]
        c["score"] = round(c["score"], 1)
    chosen.sort(key=lambda c: c["start_seq"])
    return chosen


# --- rules ----------------------------------------------------------------
def _wicket_rules(md, d, n, team, cfg, parts) -> list[dict]:  # noqa: ANN001
    out = []
    wk = d[d.n_wickets > 0]
    if not len(wk):
        return out
    seqs = list(wk.seq)
    big = {p["end_seq"]: p for p in parts if not p["unbroken"] and p["runs"] >= cfg.big_partnership}
    used_big: set[int] = set()
    # clusters
    k = 0
    while k < len(seqs):
        first = d[d.seq == seqs[k]].iloc[0]
        j = k
        while j + 1 < len(seqs):
            nxt = d[d.seq == seqs[j + 1]].iloc[0]
            if nxt.legal_balls - first.legal_balls <= cfg.cluster_balls:
                j += 1
            else:
                break
        count = int(d[(d.seq >= seqs[k]) & (d.seq <= seqs[j])].n_wickets.sum())
        if count >= cfg.cluster_min_wkts:
            last = d[d.seq == seqs[j]].iloc[0]
            win = _window(d, seqs[k], seqs[j])
            before = d[d.seq < seqs[k]]
            inn_rr = rate(int(before.total.sum()), int(before.legal.sum())) or 0
            gap = max(0.0, inn_rr - (win["run_rate"] or 0))
            bp = big.get(seqs[k])
            score = 25 * count + min(25, gap * 4) + (20 if bp else 0)
            kind = "collapse" if bp else "wicket_cluster"
            if bp:
                used_big.add(seqs[k])
            facts = {"wickets": count, "runs_in_window": win["runs"], "balls_in_window": win["balls"],
                     "window_run_rate": win["run_rate"], "innings_rr_before": inn_rr,
                     "score_before": f"{int(first.team_runs - first.total)}/{int(first.team_wkts - first.n_wickets)}",
                     "score_after": f"{int(last.team_runs)}/{int(last.team_wkts)}",
                     "partnership_ended": ({"runs": bp["runs"], "balls": bp["balls"], "batters": bp["batters"]} if bp else None),
                     "dismissed": list(md.wickets[(md.wickets.seq >= seqs[k]) & (md.wickets.seq <= seqs[j]) & md.wickets.team_wicket].player_out)}
            out.append(_tp(kind, n, team, seqs[k], seqs[j], first, last, min(score, 100), facts))
            k = j + 1
        else:
            k += 1
    # big partnerships that were broken (not already part of a collapse)
    for end_seq, p in big.items():
        if end_seq in used_big:
            continue
        r = d[d.seq == end_seq].iloc[0]
        nxt =d[(d.seq > end_seq)].head(cfg.cluster_balls // 3 or 6)
        nxt_stats = {"runs": int(nxt.total.sum()), "wickets": int(nxt.n_wickets.sum()), "balls": int(nxt.legal.sum())}
        score = 30 + min(40.0, p["runs"] / cfg.big_partnership * 20) + (15 if nxt_stats["wickets"] >= 1 else 0)
        facts = {"partnership_runs": p["runs"], "partnership_balls": p["balls"], "batters": p["batters"],
                 "wicket_no": p["wicket_no"], "dismissed": p["ended_by"],
                 "next_overs": nxt_stats if nxt_stats["balls"] >= 6 else None}
        out.append(_tp("partnership_broken", n, team, p["start_seq"], end_seq, d[d.seq == p["start_seq"]].iloc[0], r,
                       min(score, 100), facts))
    return out


def _over_rules(md, d, n, team, cfg, overs) -> list[dict]:  # noqa: ANN001
    out = []
    complete = [o for o in overs if o["complete"]]
    # high-scoring overs
    for o in complete:
        if o["runs"] >= cfg.high_over_runs:
            g = d[(d.seq >= o["start_seq"]) & (d.seq <= o["end_seq"])]
            first, last = g.iloc[0], g.iloc[-1]
            facts = {"over": o["over"], "runs": o["runs"], "fours": o["fours"], "sixes": o["sixes"], "bowlers": o["bowlers"],
                     "score_after": f"{o['cum_runs']}/{o['cum_wickets']}"}
            score = 20 + (o["runs"] - cfg.high_over_runs) * 5 + o["boundaries"] * 4
            out.append(_tp("high_scoring_over", n, team, o["start_seq"], o["end_seq"], first, last, min(score, 80), facts))
    # acceleration / slowdown on rolling windows
    W = cfg.shift_overs
    for idx in range(2 * W - 1, len(complete)):
        cur = complete[idx - W + 1: idx + 1]
        prev = complete[idx - 2 * W + 1: idx - W + 1]
        if len(cur) < W or len(prev) < W or cur[0]["over"] != prev[-1]["over"] + 1:
            continue
        c_rate = sum(o["runs"] for o in cur) / W
        p_rate = sum(o["runs"] for o in prev) / W
        delta = c_rate - p_rate
        kind = None
        if p_rate > 0 and c_rate >= p_rate * cfg.shift_ratio_up and delta >= cfg.shift_min_delta:
            kind = "acceleration"
        elif p_rate > 0 and c_rate <= p_rate * cfg.shift_ratio_down and -delta >= cfg.shift_min_delta:
            kind = "slowdown"
        if kind:
            a, b = cur[0]["start_seq"], cur[-1]["end_seq"]
            facts = {"window_overs": f"{cur[0]['over']}-{cur[-1]['over']}", "window_run_rate": round(c_rate, 2),
                     "previous_window_run_rate": round(p_rate, 2), "change_rpo": round(delta, 2),
                     "wickets_in_window": sum(o["wickets"] for o in cur), "score_after": f"{cur[-1]['cum_runs']}/{cur[-1]['cum_wickets']}"}
            out.append(_tp(kind, n, team, a, b, d[d.seq == a].iloc[0], d[d.seq == b].iloc[0],
                           min(20 + abs(delta) * 9 + (10 if kind == "slowdown" and facts["wickets_in_window"] == 0 else 0), 85), facts))
    return out


def _spell_rules(md, d, n, team, cfg) -> list[dict]:  # noqa: ANN001
    out = []
    bpo = md.balls_per_over
    for bowler, g in d.groupby("bowler"):
        ovs = sorted(g.over_no.unique())
        spells, cur = [], [ovs[0]]
        for o in ovs[1:]:
            if o - cur[-1] <= 2:  # bowlers alternate ends, so a gap of 2 overs is still one spell
                cur.append(o)
            else:
                spells.append(cur)
                cur = [o]
        spells.append(cur)
        for sp in spells:
            sg = g[g.over_no.isin(sp)]
            balls = int(sg.legal.sum())
            if len(sp) < cfg.spell_min_overs or balls < cfg.spell_min_overs * bpo:
                continue
            runs = int(sg.bowler_runs.sum())
            econ = rate(runs, balls, bpo)
            upto = d[d.seq <= sg.seq.max()]
            inn_rr = rate(int(upto.total.sum()), int(upto.legal.sum()), bpo)
            wk = int(md.wickets[(md.wickets.innings_no == n) & (md.wickets.bowler == bowler) & md.wickets.bowler_credited
                                & md.wickets.seq.between(sg.seq.min(), sg.seq.max())].shape[0])
            if econ is not None and inn_rr and econ <= cfg.spell_econ_ratio * inn_rr:
                a, b = int(sg.seq.min()), int(sg.seq.max())
                facts = {"bowler": bowler, "overs": f"{balls // bpo}.{balls % bpo}", "runs": runs, "wickets": wk,
                         "economy": econ, "innings_run_rate": inn_rr, "dots": int(((sg.bowler_runs == 0) & sg.legal).sum())}
                out.append(_tp("restrictive_spell", n, team, a, b, d[d.seq == a].iloc[0], d[d.seq == b].iloc[0],
                               min(20 + (inn_rr - econ) * 6 + wk * 10, 80), facts))
    return out


def _boundary_rules(d, n, team, cfg) -> list[dict]:  # noqa: ANN001
    out, run_start, count = [], None, 0
    rows = list(d.itertuples())
    for idx, r in enumerate(rows + [None]):
        if r is not None and (r.is_four or r.is_six):
            run_start = idx if count == 0 else run_start
            count += 1
            continue
        if count >= cfg.consecutive_boundaries:
            seg = rows[run_start: run_start + count]
            runs = sum(x.total for x in seg)
            facts = {"boundaries": count, "runs": int(runs), "sixes": int(sum(x.is_six for x in seg)),
                     "balls": len(seg), "score_after": f"{int(seg[-1].team_runs)}/{int(seg[-1].team_wkts)}"}
            out.append(_tp("boundary_burst", n, team, int(seg[0].seq), int(seg[-1].seq), seg[0], seg[-1],
                           min(25 + 12 * (count - cfg.consecutive_boundaries) + runs, 75), facts))
        count = 0
    return out


def _chase_rules(md, d, n, team, cfg) -> list[dict]:  # noqa: ANN001
    meta = md.innings_meta(n)
    if md.format == "TEST" or n < 2 or meta.get("super_over"):
        return []
    target = meta.get("target_runs") or (int(md.innings_df(1).total.sum()) + 1)
    total_overs = meta.get("target_overs") or md.overs_limit
    if not total_overs:
        return []
    bpo = md.balls_per_over
    series = []
    for ov, g in d.groupby("over_no"):
        last = g.iloc[-1]
        if g.legal.sum() < bpo:
            continue
        rem = total_overs * bpo - int(last.legal_balls)
        if rem < 12 or target - int(last.team_runs) <= 0:
            continue
        series.append((int(last.seq), int(ov), (target - int(last.team_runs)) * bpo / rem))
    out = []
    for k in range(3, len(series)):
        a, b = series[k - 3], series[k]
        delta = b[2] - a[2]
        if abs(delta) >= cfg.chase_swing_rpo:
            kind = "pressure_rise" if delta > 0 else "pressure_ease"
            facts = {"required_rate_before": round(a[2], 2), "required_rate_after": round(b[2], 2), "change_rpo": round(delta, 2),
                     "overs": f"{a[1] + 2}-{b[1] + 1}", "target": int(target)}
            s0 = d[d.seq == a[0]].iloc[0]; s1 = d[d.seq == b[0]].iloc[0]
            out.append(_tp(kind, n, team, a[0], b[0], s0, s1, min(20 + abs(delta) * 8, 80), facts))
    return out


def _tp(kind, n, team, a, b, first, last, score, facts) -> dict:  # noqa: ANN001
    return {"kind": kind, "innings_no": n, "team": team, "start_seq": int(a), "end_seq": int(b),
            "start_over": _lbl(first), "end_over": _lbl(last), "score": float(score), "facts": facts,
            "explanation": explain_turning_point({"kind": kind, "team": team, "facts": facts, "start_over": _lbl(first),
                                                  "end_over": _lbl(last)})}


def _n(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def _poss(team: str) -> str:
    return f"{team}'" if team.endswith("s") else f"{team}'s"


def explain_turning_point(tp: dict) -> str:
    """Deterministic, fact-only description (also the fallback for the LLM explainer)."""
    f, team, k = tp["facts"], tp["team"], tp["kind"]
    if k in ("collapse", "wicket_cluster"):
        s = (f"{team} lost {f['wickets']} wickets between {tp['start_over']} and {tp['end_over']} overs "
             f"({f['score_before']} to {f['score_after']}), scoring {_n(f['runs_in_window'], 'run')} from {_n(f['balls_in_window'], 'ball')}")
        if f["partnership_ended"]:
            p = f["partnership_ended"]
            s += f" after a {p['runs']}-run partnership between {' and '.join(p['batters'])} was broken"
        return s + "."
    if k == "partnership_broken":
        s = (f"The dismissal of {f['dismissed']} ended a {f['partnership_runs']}-run partnership "
             f"({f['partnership_balls']} balls) for wicket {f['wicket_no']}.")
        n = f.get("next_overs")
        if n:
            s += f" {team} then scored {n['runs']} runs and lost {n['wickets']} wicket{'s' if n['wickets'] != 1 else ''} in the next {n['balls']} balls."
        return s
    if k == "high_scoring_over":
        return (f"Over {f['over']} went for {f['runs']} runs ({f['fours']} fours, {f['sixes']} sixes) off "
                f"{' / '.join(f['bowlers'])}, moving {team} to {f['score_after']}.")
    if k in ("acceleration", "slowdown"):
        word = "rose" if k == "acceleration" else "fell"
        return (f"{_poss(team)} scoring {word} from {f['previous_window_run_rate']} to {f['window_run_rate']} runs per over in overs "
                f"{f['window_overs']} with {f['wickets_in_window']} wicket{'s' if f['wickets_in_window'] != 1 else ''} in that period "
                f"(score {f['score_after']}).")
    if k == "restrictive_spell":
        return (f"{f['bowler']} bowled {f['overs']} overs for {f['runs']} runs (economy {f['economy']} against an innings rate of "
                f"{f['innings_run_rate']}), taking {f['wickets']} wicket{'s' if f['wickets'] != 1 else ''} and slowing {team}.")
    if k == "boundary_burst":
        return (f"{team} hit {f['boundaries']} boundaries in a row ({f['sixes']} sixes) for {f['runs']} runs, reaching {f['score_after']}.")
    if k in ("pressure_rise", "pressure_ease"):
        word = "climbed" if k == "pressure_rise" else "dropped"
        return (f"The required rate {word} from {f['required_rate_before']} to {f['required_rate_after']} over overs {f['overs']} "
                f"while chasing {f['target']}.")
    return ""


# ---------------------------------------------------------------------------
def momentum_series(md: MatchData) -> list[dict]:
    """Per-over derived momentum indicator for charts. NOT a win probability.

    momentum = 50 * (rolling_rpo - innings_rpo_to_date) / max(innings_rpo_to_date, 1) - 12 * wickets_in_window
    (rolling window = the format's shift window). Positive favours the batting side's scoring, negative the bowlers.
    """
    cfg = CONFIG[md.format]
    W = max(2, cfg.shift_overs - 1) if md.format != "TEST" else 6
    series = []
    chase_info = {}
    for i in md.innings:
        n = i["innings_no"]
        target = i.get("target_runs")
        if target is None and n == 2 and md.format != "TEST" and not i.get("super_over"):
            target = int(md.innings_df(1).total.sum()) + 1
        total_overs = i.get("target_overs") or md.overs_limit
        chase_info[n] = (target, total_overs) if md.format != "TEST" and n >= 2 else (None, None)
    all_overs = over_by_over(md)
    for n in sorted(set(o["innings_no"] for o in all_overs)):
        ov = [o for o in all_overs if o["innings_no"] == n]
        target, total_overs = chase_info.get(n, (None, None))
        for k, o in enumerate(ov):
            win = ov[max(0, k - W + 1): k + 1]
            roll = sum(x["runs"] for x in win) / len(win)
            to_date = o["cum_runs"] / max(1, k + 1)
            wk_win = sum(x["wickets"] for x in win)
            mom = 50 * (roll - to_date) / max(to_date, 1.0) - 12 * wk_win
            req = None
            if target and total_overs and o["complete"]:
                rem = total_overs * md.balls_per_over - sum(x["legal_balls"] for x in ov[:k + 1])
                req = round((target - o["cum_runs"]) * md.balls_per_over / rem, 2) if rem > 0 and target > o["cum_runs"] else None
            series.append({"innings_no": n, "team": o["team"], "over": o["over"], "runs": o["runs"], "wickets": o["wickets"],
                           "cum_runs": o["cum_runs"], "cum_wickets": o["cum_wickets"], "run_rate": o["run_rate"],
                           "momentum": round(max(-100, min(100, mom)), 1), "required_rate": req,
                           "complete": o["complete"], "start_seq": o["start_seq"], "end_seq": o["end_seq"]})
    return series
