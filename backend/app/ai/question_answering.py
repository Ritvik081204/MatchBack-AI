"""'Ask MatchBack AI': route the question to a handler that computes the answer from match data in Python.

Factual answers (counts, top scorers, dismissals...) are never LLM-generated. For explanatory questions the
LLM may rephrase the computed facts, and is rejected if it introduces any figure not present in them.
"""
from __future__ import annotations

import json
import re

from ..analysis import Analysis
from . import prompt_templates as pt
from .context_builder import build_context
from .fallback_generator import (names, ordinal, plural, poss, s_bowling, s_batting, s_partnerships, s_phases, s_start,
                                 s_wickets, fallback_recap)
from .llm_service import grounding_violations, llm

WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
STOP = {"how", "the", "and", "for", "who", "out", "was", "has", "did", "get", "got", "his", "her", "are", "any", "why", "what",
        "many", "much", "most", "with", "from", "that", "this", "over", "overs", "runs", "score", "match"}
LLM_INTENTS = {"pressure", "situation", "turning", "compare", "innings_summary", "recent", "unknown"}


def _num(q: str, default: int) -> int:
    m = re.search(r"(\d+)\s*(?:overs?|balls?)", q) or re.search(r"\b(\d+)\b", q)
    if m:
        return int(m.group(1))
    for w, n in WORDNUM.items():
        if re.search(rf"\b{w}\b", q):
            return n
    return default


def find_player(a: Analysis, q: str) -> str | None:
    best, best_score = None, (0, False)
    active = {s["name"] for s in a.player_stats}  # prefer players who have actually played a part so far
    for name in a.md.all_players():
        low = name.lower()
        keys = [low] + [t for t in re.split(r"[\s.\-']+", low) if len(t) >= 3 and t not in STOP]
        for k in keys:
            score = (len(k), name in active)
            if re.search(rf"\b{re.escape(k)}\b", q) and score > best_score:
                best, best_score = name, score
    return best


def find_team(a: Analysis, q: str) -> str | None:
    hits = []
    for t in a.md.teams:
        words = [w for w in re.split(r"\s+", t.lower()) if len(w) >= 4]
        if t.lower() in q or any(re.search(rf"\b{re.escape(w)}\b", q) for w in words):
            hits.append(t)
    return hits[0] if len(hits) == 1 else None


def find_innings(q: str) -> int | None:
    for pat, n in ((r"\b(first|1st)\b", 1), (r"\b(second|2nd)\b", 2), (r"\b(third|3rd)\b", 3), (r"\b(fourth|4th)\b", 4)):
        if re.search(pat, q):
            return n
    return None


# ---- handlers -------------------------------------------------------------
def h_recent(a: Analysis, q: str, **_):
    n = _num(q, 1 if re.search(r"last over\b", q) else 5)
    cur = a.situation["innings_no"]
    ov = [o for o in a.overs if o["innings_no"] == cur][-n:]
    if not ov:
        return {"text": "No overs have been bowled yet.", "data": {}}
    runs, wk = sum(o["runs"] for o in ov), sum(o["wickets"] for o in ov)
    fours, sixes = sum(o["fours"] for o in ov), sum(o["sixes"] for o in ov)
    lo, hi = ov[0]["over"], ov[-1]["over"]
    span = f"over {hi}" if lo == hi else f"overs {lo} to {hi}"
    t = f"In the last {plural(len(ov), 'over')} ({span}), {ov[0]['team']} scored {runs} runs and lost {plural(wk, 'wicket')}, reaching {ov[-1]['cum_runs']}/{ov[-1]['cum_wickets']}."
    t += f" That included {plural(fours, 'four')} and {plural(sixes, 'six')}."  # noqa: E501
    seq_lo = ov[0]["start_seq"]
    wks = [e for e in a.timeline if e["type"] == "wicket" and e["innings_no"] == cur and e["seq"] >= seq_lo]
    if wks:
        t += " Wickets: " + "; ".join(e["description"].split(". ")[0] + f" at {e['over']}" for e in wks) + "."
    return {"text": t, "data": {"overs": [{"over": o["over"], "runs": o["runs"], "wickets": o["wickets"]} for o in ov]}}


def h_top_scorer(a: Analysis, **_):
    bats = sorted([s for s in a.player_stats if s["batting"] and s["batting"]["balls"]], key=lambda s: -s["batting"]["runs"])[:3]
    if not bats:
        return {"text": "No batting data is available yet.", "data": {}}
    f = lambda s: f"{s['name']} ({s['team']}) {s['batting']['runs']} off {s['batting']['balls']} balls"  # noqa: E731
    t = f"{f(bats[0])} has scored the most runs."
    if len(bats) > 1:
        t += " Next: " + "; ".join(f(s) for s in bats[1:]) + "."
    if a.md.format == "TEST":
        t += " Totals are summed across innings."
    return {"text": t, "data": {"top": [s["name"] for s in bats]}}


def h_top_wickets(a: Analysis, **_):
    bw = sorted([s for s in a.player_stats if s["bowling"] and s["bowling"]["wickets"]],
                key=lambda s: (-s["bowling"]["wickets"], s["bowling"]["runs"]))[:3]
    if not bw:
        return {"text": "No bowler has taken a wicket yet.", "data": {}}
    f = lambda s: f"{s['name']} ({s['team']}) {s['bowling']['wickets']}/{s['bowling']['runs']} in {s['bowling']['overs']} overs"  # noqa: E731
    t = f"{f(bw[0])} leads the bowlers."
    if len(bw) > 1:
        t += " Next: " + "; ".join(f(s) for s in bw[1:]) + "."
    return {"text": t, "data": {"top": [s["name"] for s in bw]}}


def h_boundaries(a: Analysis, q: str, player=None, team=None, **_):
    d = a.md.deliveries
    what = "sixes" if "six" in q else "fours" if "four" in q else "boundaries"
    if player:
        d = d[d.batter == player]
    elif team:
        d = d[d.batting_team == team]
    fours, sixes = int(d.is_four.sum()), int(d.is_six.sum())
    n = {"sixes": sixes, "fours": fours, "boundaries": fours + sixes}[what]
    word = what if n != 1 else {"sixes": "six", "fours": "four", "boundaries": "boundary"}[what]
    who = f" by {player}" if player else f" by {team}" if team else ""
    t = f"{n} {word}{who}"
    if not player and not team:
        per = {tm: (int(g.is_four.sum()), int(g.is_six.sum())) for tm, g in d.groupby("batting_team")}
        t += " in total (" + "; ".join(f"{tm}: {plural(f, 'four')}, {plural(s, 'six')}" for tm, (f, s) in per.items()) + ")"
    return {"text": t + ".", "data": {"fours": fours, "sixes": sixes}}


def h_partnership(a: Analysis, team=None, innings=None, **_):
    ps = [p for p in a.partnerships if (not team or p["team"] == team) and (not innings or p["innings_no"] == innings)]
    if not ps:
        return {"text": "No partnership data is available yet.", "data": {}}
    best = max(ps, key=lambda p: p["runs"])
    t = (f"The biggest partnership is {best['runs']} between {names(best['batters'])} for {best['team']} "
         f"({best['balls']} balls, {ordinal(best['wicket_no'])} wicket{', still unbroken' if best['unbroken'] else ''}).")
    open_ = [p for p in ps if p["unbroken"] and p["innings_no"] == a.situation["innings_no"] and p is not best]
    if open_:
        o = open_[0]
        t += f" The current partnership is {o['runs']} between {names(o['batters'])} ({o['balls']} balls)."
    return {"text": t, "data": {"runs": best["runs"]}}


def h_turning(a: Analysis, **_):
    tps = sorted(a.turning_points, key=lambda t: t["rank"])[:3]
    if not tps:
        return {"text": "No statistically significant turning points have been detected yet.", "data": {}}
    t = "The biggest turning points so far (ranked by measured impact): " + " ".join(
        f"{i}. ({x['team']}, overs {x['start_over']}-{x['end_over']}) {x['explanation']}" for i, x in enumerate(tps, 1))
    return {"text": t, "data": {"ids": [x["id"] for x in tps]}}


def h_milestones(a: Analysis, **_):
    ms = [m for m in a.milestones if not m["superseded"] and m["category"] != "team"]
    ms.sort(key=lambda m: -m["seq"])
    if not ms:
        return {"text": "No individual or partnership milestones have been reached yet.", "data": {}}
    t = "Milestones so far: " + " ".join(f"({m['team']}, {m['over']}) {m['detail']}" for m in ms[:5])
    return {"text": t, "data": {"count": len(ms)}}


def h_pressure(a: Analysis, q: str, team=None, **_):
    s = a.situation
    bat, bowl = s["batting_team"], s["bowling_team"]
    team = team or bat
    if team != bat:
        t = f"{bat} are batting; {team} are bowling. {bat} are {s['score']} after {s['overs']} overs"
        t += f" and need {s['runs_needed']} more (required rate {s['required_rate']})." if s["runs_needed"] and s["required_rate"] else "."
        return {"text": t, "data": {}}
    reasons = []
    if s["required_rate"] and s["run_rate"] is not None:
        reasons.append(f"the required rate is {s['required_rate']} against a current rate of {s['run_rate']} (needing {s['runs_needed']} from {s['balls_remaining']} balls)")
    if s["wickets"] >= 4:
        reasons.append(f"{plural(s['wickets'], 'wicket')} have fallen")
    cur = [o for o in a.overs if o["innings_no"] == s["innings_no"]][-3:]
    if cur and sum(o["wickets"] for o in cur) >= 1:
        reasons.append(f"{plural(sum(o['wickets'] for o in cur), 'wicket')} fell in the last {len(cur)} overs")
    if cur and s["run_rate"] and len(cur) >= 3 and sum(o["runs"] for o in cur) / len(cur) < s["run_rate"] - 1:
        reasons.append(f"scoring has slowed to {round(sum(o['runs'] for o in cur) / len(cur), 1)} an over in the last {len(cur)} overs")
    tp = [t for t in a.turning_points if t["team"] == team and t["innings_no"] == s["innings_no"]]
    if tp:
        reasons.append(tp[-1]["explanation"].rstrip("."))
    adv = s.get("advantage")
    if not reasons:
        return {"text": f"By the measured indicators {team} do not look under particular pressure ({s['score']} after {s['overs']} overs, run rate {s['run_rate']}).", "data": {}}
    t = f"{team} are {s['score']} after {s['overs']} overs. Indicators pointing to pressure: " + "; ".join(reasons) + "."
    if adv and adv.get("label"):
        t += f" Overall heuristic: {adv['label'].lower()} (not a win probability)."
    return {"text": t, "data": {"reasons": len(reasons)}}


def h_situation(a: Analysis, **_):
    ctx = build_context(a, "quick", "situation")
    return {"text": " ".join(fallback_recap(ctx)), "data": {}}


def h_innings_summary(a: Analysis, innings=None, **_):
    ctx = build_context(a, "standard", "everything")
    n = innings or (1 if len(ctx["innings"]) > 1 else ctx["innings"][0]["no"])
    inn = next((i for i in ctx["innings"] if i["no"] == n), None)
    if not inn:
        return {"text": f"Innings {n} has not started at this point of the match.", "data": {}}
    head = f"Innings {n}: {inn['team']} {inn['score']} after {inn['overs']} overs (run rate {inn['run_rate']})."
    parts = [head, s_start(ctx, inn), s_phases(inn), s_partnerships(inn), s_wickets(inn, 5), s_batting(inn, 2), s_bowling(inn, 2)]
    return {"text": " ".join(p for p in parts if p), "data": {"innings": n}}


def h_compare(a: Analysis, **_):
    d = a.md.deliveries
    lines = []
    for inn in a.situation["innings_summary"]:
        g = d[d.innings_no == inn["innings_no"]]
        card = next(c for c in a.scorecard if c["innings_no"] == inn["innings_no"])
        top = max(card["batters"], key=lambda b: b["runs"], default=None)
        bw = max(card["bowling"], key=lambda b: (b["wickets"], -b["runs"]), default=None)
        lines.append(f"{inn['team']} (innings {inn['innings_no']}): {inn['runs']}/{inn['wickets']} in {inn['overs']} overs, run rate {inn['run_rate']}, "
                     f"{plural(int(g.is_four.sum()), 'four')} and {plural(int(g.is_six.sum()), 'six')}, {inn['extras']} extras; top scorer {top['name']} {top['runs']}"
                     + (f"; best bowler against them {bw['name']} {bw['wickets']}/{bw['runs']}" if bw and bw["wickets"] else "") + ".")
    return {"text": " ".join(lines), "data": {}}


def h_wickets_count(a: Analysis, team=None, **_):
    parts = []
    for inn in a.situation["innings_summary"]:
        if team and inn["team"] != team:
            continue
        w = a.md.wickets[(a.md.wickets.innings_no == inn["innings_no"]) & a.md.wickets.team_wicket]
        kinds = w.kind.value_counts().to_dict()
        parts.append(f"{inn['team']} (innings {inn['innings_no']}) have lost {plural(inn['wickets'], 'wicket')}"
                     + (f" ({', '.join(f'{v} {k}' for k, v in kinds.items())})" if kinds else ""))
    return {"text": "; ".join(parts) + "." if parts else "No wickets recorded.", "data": {}}


def h_extras(a: Analysis, **_):
    parts = []
    for c in a.scorecard:
        e = c["extras"]
        parts.append(f"{c['team']} (innings {c['innings_no']}) received {e['total']} extras ({e['wides']} wides, {e['noballs']} no-balls, {e['byes']} byes, {e['legbyes']} leg-byes)")
    return {"text": "; ".join(parts) + ".", "data": {}}


def h_player_out(a: Analysis, player=None, **_):
    if not player:
        return {"text": "Tell me which player you mean (e.g. 'How did Kohli get out?').", "data": {}}
    w = a.md.wickets[(a.md.wickets.player_out == player) & a.md.wickets.team_wicket]
    if not len(w):
        s = next((x for x in a.player_stats if x["name"] == player), None)
        if s and s["batting"]:
            b = s["batting"]
            if b["balls"] == 0:
                return {"text": f"{player} is at the crease but has not faced a ball yet.", "data": {}}
            return {"text": f"{player} has not been dismissed - {b['runs']} not out from {b['balls']} balls.", "data": {}}
        return {"text": f"{player} has not batted yet in this match.", "data": {}}
    parts = []
    for r in w.itertuples():
        ev = next((e for e in a.timeline if e["type"] == "wicket" and e["seq"] == r.seq and player in e["players"]), None)
        parts.append(f"{ev['description']} That was at {ev['over']} overs." if ev else f"{player} was out ({r.kind}).")
    return {"text": " ".join(parts), "data": {}}


def h_player_stats(a: Analysis, player=None, **_):
    s = next((x for x in a.player_stats if x["name"] == player), None)
    if not s:
        return {"text": f"{player} has no recorded batting or bowling in this match so far.", "data": {}}
    from .fallback_generator import batting_insight, bowling_insight
    return {"text": " ".join(x for x in (batting_insight(s), bowling_insight(s)) if x), "data": {}}


def h_result(a: Analysis, q: str, **_):
    md, s = a.md, a.situation
    if "toss" in q:
        return {"text": f"{md.meta['toss_winner']} won the toss and chose to {md.meta['toss_decision']}." if md.meta.get("toss_winner") else "Toss information is not available.", "data": {}}
    if "venue" in q or "where" in q:
        return {"text": f"Played at {md.meta.get('venue') or 'an unrecorded venue'}{', ' + md.meta['city'] if md.meta.get('city') else ''}.", "data": {}}
    if not s["completed"]:
        return {"text": f"The match is still in progress at this point ({s['status']}), so there is no result yet - and I will not guess one.", "data": {}}
    t = md.result["text"] + "."
    if md.result["player_of_match"]:
        t += f" Player of the match: {names(md.result['player_of_match'])}."
    return {"text": t, "data": {}}


def h_highlight(a: Analysis, q: str, **_):
    h = a.highlights
    if "strike" in q:
        x = h["best_strike_rate"]
        return {"text": (f"{x['name']} ({x['team']}) has the best strike rate: {x['strike_rate']} ({x['runs']} off {x['balls']}; minimum {x['min_balls']} balls)." if x
                         else "No batter has faced enough balls yet for a meaningful strike-rate ranking."), "data": {}}
    x = h["best_economy"]
    return {"text": (f"{x['name']} ({x['team']}) has the best economy: {x['economy']} over {x['overs']} overs (minimum {x['min_balls'] // a.md.balls_per_over} overs)." if x
                     else "No bowler has bowled enough overs yet for a meaningful economy ranking."), "data": {}}


ROUTES: list[tuple[str, str]] = [
    ("recent", r"\b(last|past|previous|latest)\b.*\bovers?\b|\brecent(ly)?\b|what just happened|last over"),
    ("player_out", r"(how|when).*(out|dismiss)|dismissal of|got out|get out|was .* out"),
    ("partnership", r"partnership|stand\b"),
    ("turning", r"turning point|key moment|biggest moment|changed the (game|match)|momentum|swing|crucial|decisive"),
    ("milestones", r"milestone|century|centuries|fifty|half.?century|hundred|five.wicket|fifer|achiev|record"),
    ("boundaries", r"how many (sixes|fours|boundaries)|number of (sixes|fours|boundaries)|\bsixes\b|\bfours\b"),
    ("top_wickets", r"most wickets|top wicket|best bowler|leading wicket|highest wicket|who took the most|wicket.?taker"),
    ("top_scorer", r"most runs|top scor|highest scor|leading run|who scored the most|best batter|best batsman|run.?scorer"),
    ("highlight", r"strike rate|economy"),
    ("pressure", r"pressure|struggl|in trouble|required rate"),
    ("compare", r"compar|\bversus\b|\bvs\b|both teams|team performance|which team (is|has)"),
    ("innings_summary", r"summar\w+.*innings|innings.*summar|(first|second|third|fourth|1st|2nd|3rd|4th) innings"),
    ("wickets_count", r"how many wickets|wickets (have|has)|wickets lost|wickets fallen"),
    ("extras", r"extras|wides|no.?balls|byes"),
    ("result", r"who won|result|winner|player of the match|man of the match|\btoss\b|venue|where (is|was)"),
    ("situation", r"situation|current|run rate|where are we|who is (winning|ahead|leading)|status|catch me up|summar|score"),
]


def classify(q: str) -> str:
    for intent, pat in ROUTES:
        if re.search(pat, q):
            return intent
    return "unknown"


HANDLERS = {
    "recent": h_recent, "player_out": h_player_out, "partnership": h_partnership, "turning": h_turning, "milestones": h_milestones,
    "boundaries": h_boundaries, "top_wickets": h_top_wickets, "top_scorer": h_top_scorer, "highlight": h_highlight, "pressure": h_pressure,
    "compare": h_compare, "innings_summary": h_innings_summary, "wickets_count": h_wickets_count, "extras": h_extras,
    "result": h_result, "situation": h_situation,
}


def suggestions(a: Analysis) -> list[str]:
    s = a.situation
    out = ["Explain the current match situation", "What happened in the last five overs?", "Who scored the most runs?",
           "Which bowler has taken the most wickets?", "What were the major turning points?", "What was the biggest partnership?",
           "How many sixes were hit?", "Which player achieved a milestone?", "Compare both teams' performances"]
    if s["innings_no"] >= 2 and not s["innings_finished"]:
        out.insert(1, f"Why is {s['batting_team']} under pressure?")
        out.append("Summarize the first innings")
    top = a.highlights.get("top_scorer")
    if top:
        out.append(f"How did {top['name'].split()[-1]} get out?")
    return out


def answer_question(a: Analysis, question: str, use_llm: bool = True) -> dict:
    q = question.lower().strip()
    if not q:
        return {"answer": "Ask me anything about this match.", "intent": "empty", "engine": "rule-based", "grounded": True,
                "suggestions": suggestions(a)}
    player, team, innings = find_player(a, q), find_team(a, q), find_innings(q)
    intent = classify(q)
    if intent == "unknown" and player:
        intent = "player_stats"
    handler = HANDLERS.get(intent, h_player_stats) if intent != "unknown" else None
    kw = dict(a=a, q=q, player=player, team=team, innings=innings)

    if handler is None:
        text = ("I can't answer that from the match data I have. I can cover scores, run-scorers, wickets, partnerships, "
                "milestones, turning points, recent overs, dismissals and comparisons - try one of the suggestions below.")
        result = {"text": text, "data": {}}
    else:
        result = handler(**kw)

    engine, answer, grounded = "rule-based (computed from match data)", result["text"], True
    if use_llm and intent in LLM_INTENTS and intent != "unknown" and llm.available:
        ctx_json = json.dumps(build_context(a, "quick", "situation"), separators=(",", ":"), default=str)
        out = llm.generate(pt.QA_SYSTEM, pt.qa_prompt(question, result["text"], ctx_json), 220)
        if out and len(grounding_violations(out, result["text"] + ctx_json)) <= 1:
            answer, engine = out, f"ollama:{llm.model} (grounded on computed facts)"
        elif out:
            grounded = True  # fell back to the computed text; LLM output rejected
    return {"answer": answer, "facts_text": result["text"], "intent": intent, "engine": engine, "grounded": grounded,
            "entities": {"player": player, "team": team, "innings": innings}, "data": result["data"],
            "suggestions": [] if handler else suggestions(a)[:6]}
