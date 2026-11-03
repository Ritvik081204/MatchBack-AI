"""Builds the compact, structured fact context given to the LLM / fallback generator.

Everything comes from the cached `Analysis` (computed from the match data) - never raw ball-by-ball rows.
Size is bounded by (length, focus), which also keeps local-model latency low.
"""
from __future__ import annotations

from ..analysis import Analysis

LIMITS = {  # items per list by recap length
    "quick": {"batters": 2, "bowlers": 2, "tps": 1, "miles": 2, "events": 3, "recent": 2, "partnerships": 1},
    "standard": {"batters": 3, "bowlers": 3, "tps": 3, "miles": 4, "events": 5, "recent": 3, "partnerships": 2},
    "detailed": {"batters": 4, "bowlers": 4, "tps": 5, "miles": 8, "events": 8, "recent": 5, "partnerships": 3},
}


def _figures(b: dict) -> str:
    return f"{b['wickets']}/{b['runs']} ({b['overs']} ov)"


def _batter_view(b: dict) -> dict:
    return {"name": b["name"], "runs": b["runs"], "balls": b["balls"], "fours": b["fours"], "sixes": b["sixes"],
            "strike_rate": b["strike_rate"], "out": b["out"], "how_out": b["dismissal"] if b["out"] else "not out"}


def build_context(a: Analysis, length: str = "standard", focus: str = "everything") -> dict:
    md, sit = a.md, a.situation
    lim = LIMITS[length]
    result_known = md.complete and sit["completed"]
    ctx: dict = {
        "match": {"title": md.title, "format": md.format, "tournament": md.meta.get("tournament"), "venue": md.meta.get("venue"),
                  "toss": f"{md.meta.get('toss_winner')} chose to {md.meta.get('toss_decision')}" if md.meta.get("toss_winner") else None,
                  "result": md.result["text"] if result_known else None,
                  "note": "Result is known." if result_known else "Match is in progress at this point; the final result is unknown and must not be guessed."},
        "now": {k: sit[k] for k in ("innings_no", "batting_team", "bowling_team", "score", "overs", "run_rate", "target", "required_rate",
                                    "runs_needed", "balls_remaining", "lead", "projected", "status", "current_batters", "current_bowler",
                                    "innings_finished")},
        "advantage_heuristic": sit["advantage"],
        "innings": [],
    }
    for inn in sit["innings_summary"]:
        n = inn["innings_no"]
        card = next(c for c in a.scorecard if c["innings_no"] == n)
        batters = sorted([b for b in card["batters"] if b["balls"] > 0], key=lambda b: -b["runs"])[: lim["batters"]]
        bowlers = sorted(card["bowling"], key=lambda b: (-b["wickets"], b["economy"] or 99))[: lim["bowlers"]]
        fow = card["fall_of_wickets"]
        parts = sorted([p for p in a.partnerships if p["innings_no"] == n], key=lambda p: -p["runs"])[: lim["partnerships"]]
        ctx["innings"].append({
            "no": n, "team": inn["team"], "score": f"{inn['runs']}/{inn['wickets']}", "overs": inn["overs"], "run_rate": inn["run_rate"],
            "finished": inn["finished"], "extras": inn["extras"],
            "phases": [{"name": p["name"], "overs": f"{p['from_over']}-{p['to_over']}", "runs": p["runs"], "wickets": p["wickets"],
                        "run_rate": p["run_rate"], "complete": p["complete"]} for p in a.phases.get(n, [])],
            "batters": [_batter_view(b) for b in batters],
            "bowlers": [{"name": b["name"], "figures": _figures(b), "economy": b["economy"], "maidens": b["maidens"]} for b in bowlers],
            "first_wicket": {"score": f"{fow[0]['runs']}/1", "over": fow[0]["over"], "player": fow[0]["player"]} if fow else None,
            "wickets_fallen": [{"no": f["wicket_no"], "player": f["player"], "score": f"{f['runs']}/{f['wicket_no']}", "over": f["over"]}
                               for f in fow][: (10 if focus == "wickets" or length == "detailed" else 5)],
            "partnerships": [{"batters": p["batters"], "runs": p["runs"], "balls": p["balls"], "wicket_no": p["wicket_no"],
                              "unbroken": p["unbroken"], "overs": f"{p['start_over']}-{p['end_over']}"} for p in parts],
        })
    tps = sorted(a.turning_points, key=lambda t: t["rank"])[: lim["tps"] + (2 if focus == "wickets" else 0)]
    ctx["turning_points"] = [{"rank": t["rank"], "innings": t["innings_no"], "team": t["team"], "overs": f"{t['start_over']}-{t['end_over']}",
                              "kind": t["label"], "text": t["explanation"]} for t in tps]
    ms = [m for m in a.milestones if not m["superseded"]]
    ms.sort(key=lambda m: (-{"batting": 3, "bowling": 3, "partnership": 2, "team": 1}[m["category"]] * (2 if focus == "milestones" else 1),
                           -m["threshold"]))
    ctx["milestones"] = [{"innings": m["innings_no"], "over": m["over"], "category": m["category"], "text": m["detail"]}
                         for m in ms[: lim["miles"] + (4 if focus == "milestones" else 0)]]
    recent = a.overs[-lim["recent"] - (2 if focus == "situation" else 0):]
    ctx["recent_overs"] = [{"innings": o["innings_no"], "over": o["over"], "runs": o["runs"], "wickets": o["wickets"],
                            "bowlers": o["bowlers"], "score_after": f"{o['cum_runs']}/{o['cum_wickets']}", "complete": o["complete"]}
                           for o in recent]
    events = sorted([e for e in a.timeline if e["type"] in ("wicket", "milestone", "big_over")], key=lambda e: -e["importance"])[: lim["events"]]
    ctx["key_events"] = [{"innings": e["innings_no"], "over": e["over"], "text": e["description"]} for e in sorted(events, key=lambda e: e["seq"])]
    h = a.highlights
    ctx["performers"] = {k: v for k, v in h.items() if v and k in ("top_scorer", "top_wicket_taker", "best_strike_rate", "best_economy", "all_round")}
    ctx["focus"], ctx["length"] = focus, length
    return ctx
