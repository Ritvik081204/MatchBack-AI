"""Automatic milestone detection. Each milestone is emitted exactly once, at the ball that achieves it.

Only facts present in the supplied match data are reported:
* "fastest" claims are limited to *this match* (no external historical comparison data is bundled)
* career milestones are never inferred from a single match - they are listed as unavailable
"""
from __future__ import annotations

from .match_processor import MatchData
from .statistics import partnerships

BAT_STEPS = (30, 50, 100, 150, 200, 250, 300)
BOWL_STEPS = (3, 4, 5)
TEAM_STEPS = {
    "T20": (50, 100, 150, 200, 250),
    "ODI": (50, 100, 150, 200, 250, 300, 350, 400, 450),
    "TEST": (100, 200, 300, 400, 500, 600, 700),
}

BAT_BADGE = {30: "30 UP", 50: "HALF-CENTURY!", 100: "CENTURY ALERT!", 150: "150 RUNS!", 200: "DOUBLE CENTURY!",
             250: "250 RUNS!", 300: "TRIPLE CENTURY!"}
BOWL_BADGE = {3: "3-WICKET HAUL", 4: "4-WICKET HAUL", 5: "FIVE-WICKET HAUL!", 10: "10 WICKETS IN THE MATCH!"}

UNAVAILABLE = [
    {"kind": "career", "reason": "Career milestones need verified career data; a single-match dataset cannot support them."},
    {"kind": "fastest_vs_history", "reason": "No historical comparison dataset is bundled, so fastest-ever claims are not made. "
                                             "'Fastest in this match' is shown where applicable."},
]


def _label(r) -> str:  # noqa: ANN001
    return f"{r.over_no}.{r.ball_no}"


def detect_milestones(md: MatchData) -> list[dict]:
    out: list[dict] = []
    d = md.deliveries
    fmt = md.format

    for i in md.innings:
        n = i["innings_no"]
        team = i["team"]
        opp = next(t for t in md.teams if t != team)
        bat: dict[str, dict] = {}
        bowl: dict[str, dict] = {}
        prev_team = 0
        for r in d[d.innings_no == n].itertuples():
            # --- batting ---
            b = bat.setdefault(r.batter, {"runs": 0, "balls": 0, "fours": 0, "sixes": 0})
            before = b["runs"]
            b["runs"] += int(r.batter_runs); b["balls"] += int(r.faced)
            b["fours"] += int(r.is_four); b["sixes"] += int(r.is_six)
            for step in BAT_STEPS:
                if before < step <= b["runs"]:
                    out.append({
                        "category": "batting", "kind": f"bat_{step}", "threshold": step, "seq": int(r.seq), "innings_no": n,
                        "over": _label(r), "team": team, "players": [r.batter], "badge": BAT_BADGE[step],
                        "title": f"{r.batter} reaches {step}" if step != 100 else f"{r.batter} scores a century",
                        "detail": f"{r.batter} has scored {b['runs']} runs from {b['balls']} balls "
                                  f"({b['fours']} fours, {b['sixes']} sixes) for {team}.",
                        "stats": {"runs": b["runs"], "balls": b["balls"], "fours": b["fours"], "sixes": b["sixes"],
                                  "strike_rate": round(b["runs"] * 100 / b["balls"], 2) if b["balls"] else None},
                    })
            # --- bowling ---
            if r.is_wicket:
                for w in md.wickets[md.wickets.seq == r.seq].itertuples():
                    if not w.bowler_credited:
                        continue
                    bw = bowl.setdefault(w.bowler, {"wk": 0})
                    bw["wk"] += 1
                    if bw["wk"] in BOWL_STEPS:
                        g = d[(d.innings_no == n) & (d.bowler == w.bowler) & (d.seq <= r.seq)]
                        runs, balls = int(g.bowler_runs.sum()), int(g.legal.sum())
                        out.append({
                            "category": "bowling", "kind": f"bowl_{bw['wk']}w", "threshold": bw["wk"], "seq": int(r.seq),
                            "innings_no": n, "over": _label(r), "team": opp, "players": [w.bowler],
                            "badge": BOWL_BADGE[bw["wk"]], "title": f"{w.bowler} takes {bw['wk']} wickets",
                            "detail": f"{w.bowler} has {bw['wk']} wickets for {runs} runs in "
                                      f"{balls // md.balls_per_over}.{balls % md.balls_per_over} overs this innings.",
                            "stats": {"wickets": bw["wk"], "runs": runs, "legal_balls": balls},
                        })
            # --- team ---
            for step in TEAM_STEPS[fmt]:
                if prev_team < step <= r.team_runs:
                    out.append({
                        "category": "team", "kind": f"team_{step}", "threshold": step, "seq": int(r.seq), "innings_no": n,
                        "over": _label(r), "team": team, "players": [], "badge": f"{step} UP",
                        "title": f"{team} reach {step}",
                        "detail": f"{team} bring up {step} runs for {int(r.team_wkts)} "
                                  f"wicket{'s' if r.team_wkts != 1 else ''} in {r.legal_balls // md.balls_per_over}."
                                  f"{r.legal_balls % md.balls_per_over} overs.",
                        "stats": {"runs": int(r.team_runs), "wickets": int(r.team_wkts), "legal_balls": int(r.legal_balls)},
                    })
            prev_team = int(r.team_runs)

    # Test: 10 wickets in the match by one bowler (across innings)
    if fmt == "TEST":
        tally: dict[str, int] = {}
        for w in md.wickets[md.wickets.bowler_credited].itertuples():
            tally[w.bowler] = tally.get(w.bowler, 0) + 1
            if tally[w.bowler] == 10:
                r = d[d.seq == w.seq].iloc[0]
                out.append({
                    "category": "bowling", "kind": "bowl_10w_match", "threshold": 10, "seq": int(w.seq),
                    "innings_no": int(w.innings_no), "over": f"{r.over_no}.{r.ball_no}",
                    "team": next(t for t in md.teams if t != r.batting_team), "players": [w.bowler],
                    "badge": BOWL_BADGE[10], "title": f"{w.bowler} completes a 10-wicket match haul",
                    "detail": f"{w.bowler} has now taken 10 wickets in this Test.", "stats": {"wickets": 10},
                })

    # partnerships
    for p in partnerships(md):
        for s in p["steps"]:
            if s["step"] < 50:
                continue
            g = d[(d.innings_no == p["innings_no"]) & (d.seq >= p["start_seq"]) & (d.seq <= s["seq"])]
            balls = int(g.legal.sum())
            out.append({
                "category": "partnership", "kind": f"partnership_{s['step']}", "threshold": s["step"], "seq": s["seq"],
                "innings_no": p["innings_no"], "over": s["label"], "team": p["team"], "players": p["batters"],
                "badge": f"{s['step']}-RUN STAND!",
                "title": f"{s['step']}-run partnership: {' & '.join(p['batters'])}",
                "detail": f"{' and '.join(p['batters'])} have added {s['step']} runs for wicket {p['wicket_no']} "
                          f"off {balls} balls for {p['team']}.",
                "stats": {"runs": s["step"], "balls": balls, "wicket_no": p["wicket_no"]},
            })

    out.sort(key=lambda m: (m["seq"], m["category"]))
    _annotate(out)
    for k, m in enumerate(out):
        m["id"] = f"ms-{m['seq']}-{m['kind']}-{k}"
    return out


def _annotate(ms: list[dict]) -> None:
    """Mark superseded batting/bowling steps and 'fastest in this match' claims (in-match comparison only)."""
    best: dict[tuple, dict] = {}
    for m in ms:
        if m["category"] in ("batting", "bowling"):
            best[(m["category"], m["players"][0], m["innings_no"])] = m
    for m in ms:
        if m["category"] in ("batting", "bowling"):
            m["superseded"] = best[(m["category"], m["players"][0], m["innings_no"])] is not m
        else:
            m["superseded"] = False
    for kind in ("bat_50", "bat_100"):
        group = [m for m in ms if m["kind"] == kind]
        if len(group) >= 2:
            fastest = min(group, key=lambda m: m["stats"]["balls"])
            if sum(1 for m in group if m["stats"]["balls"] == fastest["stats"]["balls"]) == 1:
                fastest["match_fastest"] = True
                fastest["detail"] += f" Fastest {'fifty' if kind == 'bat_50' else 'hundred'} of this match."
