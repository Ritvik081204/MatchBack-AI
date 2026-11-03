"""Deterministic natural-language generation from the structured context.

This is both the offline fallback (no Ollama) and the safety net when an LLM answer fails the grounding check.
Every number it writes comes straight from the context dict.
"""
from __future__ import annotations

WORD_TARGET = {"quick": 75, "standard": 160, "detailed": 340}


def ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 'es' if word.endswith(('x', 's')) else 's'}"


def names(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1] if xs else ""


def poss(team: str) -> str:
    return f"{team}'" if team.endswith("s") else f"{team}'s"


# ---- sections -------------------------------------------------------------
def s_situation(ctx: dict) -> str:
    n, mt = ctx["now"], ctx["match"]
    if mt["result"]:
        last = ctx["innings"][-1]
        return f"{mt['result']}. {last['team']} finished on {last['score']} after {last['overs']} overs."
    base = f"{n['batting_team']} are {n['score']} after {n['overs']} overs"
    if n["run_rate"] is not None:
        base += f" (run rate {n['run_rate']})"
    if n["innings_finished"]:
        return f"{n['batting_team']} finished their innings on {n['score']} after {n['overs']} overs ({n['status']})."
    if n["target"] and n["runs_needed"] is not None and n["innings_no"] >= 2:
        if n["balls_remaining"] is not None:
            base += f", chasing {n['target']}: they need {n['runs_needed']} from {n['balls_remaining']} balls"
            if n["required_rate"]:
                base += f" (required rate {n['required_rate']})"
        else:
            base += f", chasing {n['target']} and need {n['runs_needed']} more"
    elif n["lead"] is not None:
        base += f" and {'lead by ' + str(n['lead']) if n['lead'] > 0 else 'trail by ' + str(-n['lead']) if n['lead'] < 0 else 'are level'}"
    elif n["projected"]:
        base += f", a projection of {n['projected']} at the current rate"
    s = base + "."
    adv = ctx.get("advantage_heuristic")
    if adv and adv.get("label") and adv["label"] != "Too early to call":
        s += f" Indicator: {adv['label'].lower()} (a heuristic based on required vs current rate and wickets, not a win probability)."
    return s


def s_start(ctx: dict, inn: dict) -> str | None:
    bits = []
    ph = inn["phases"][0] if inn["phases"] else None
    if ph:
        bits.append(f"{inn['team']} made {ph['runs']}/{ph['wickets']} in the {ph['name'].lower()} (overs {ph['overs']}) at {ph['run_rate']} an over"
                    + ("" if ph["complete"] else " so far"))
    fw = inn["first_wicket"]
    if fw:
        bits.append(f"the first wicket, {fw['player']}, fell at {fw['score']} in over {fw['over']}")
    elif ph:
        bits.append("no wicket had fallen in that spell")
    return (bits[0][0].upper() + bits[0][1:] + (" and " + bits[1] if len(bits) > 1 else "") + ".") if bits else None


def s_phases(inn: dict) -> str | None:
    ps = inn["phases"][1:]
    if not ps:
        return None
    parts = [f"{p['runs']}/{p['wickets']} in the {p['name'].lower()} (overs {p['overs']}, {p['run_rate']} an over)" for p in ps]
    return f"After that, {inn['team']} scored {names(parts)}."


def s_partnerships(inn: dict) -> str | None:
    if not inn["partnerships"]:
        return None
    p = inn["partnerships"][0]
    s = f"The biggest partnership for {inn['team']} so far is {p['runs']} between {names(p['batters'])} ({p['balls']} balls, for the {ordinal(p['wicket_no'])} wicket"
    s += ", still unbroken)." if p["unbroken"] else ")."
    if len(inn["partnerships"]) > 1:
        q = inn["partnerships"][1]
        s += f" Another useful stand was {q['runs']} between {names(q['batters'])}."
    return s


def s_wickets(inn: dict, limit: int = 5) -> str | None:
    w = inn["wickets_fallen"][:limit]
    if not w:
        return f"{inn['team']} have not lost a wicket." if inn["batters"] else None
    parts = [f"{x['player']} ({x['score']}, over {x['over']})" for x in w]
    more = "" if len(inn["wickets_fallen"]) <= limit else f", with {len(inn['wickets_fallen']) - limit} more after that"
    return f"Wickets for {inn['team']}: {names(parts)}{more}."


def s_batting(inn: dict, k: int = 2) -> str | None:
    bs = inn["batters"][:k]
    if not bs:
        return None
    parts = []
    for b in bs:
        t = f"{b['name']} {b['runs']}{'' if b['out'] else '*'} ({b['balls']})"
        if b["fours"] or b["sixes"]:
            t += f" with {plural(b['fours'], 'four')} and {plural(b['sixes'], 'six')}" if b["sixes"] else f" with {plural(b['fours'], 'four')}"
        if b["strike_rate"] is not None and b["balls"] >= 10:
            t += f", strike rate {b['strike_rate']}"
        parts.append(t)
    return f"With the bat for {inn['team']}: {'; '.join(parts)}."


def s_bowling(inn: dict, k: int = 2) -> str | None:
    bs = [b for b in inn["bowlers"] if b["figures"] != "0/0 (0.0 ov)"][:k]
    if not bs:
        return None
    parts = [f"{b['name']} {b['figures']}, economy {b['economy']}" for b in bs]
    return f"Best with the ball against {inn['team']}: {'; '.join(parts)}."


def s_turning(ctx: dict, k: int) -> str | None:
    tps = ctx["turning_points"][:k]
    if not tps:
        return None
    return "Key turning points: " + " ".join(f"({t['overs']}) {t['text']}" for t in tps)


def s_milestones(ctx: dict, k: int) -> str | None:
    ms = ctx["milestones"][:k]
    return ("Milestones: " + " ".join(m["text"] for m in ms)) if ms else None


def s_recent(ctx: dict) -> str | None:
    ov = [o for o in ctx["recent_overs"] if o["innings"] == ctx["now"]["innings_no"]]
    if not ov:
        return None
    runs, wk = sum(o["runs"] for o in ov), sum(o["wickets"] for o in ov)
    first, last = ov[0]["over"], ov[-1]["over"]
    span = f"over {last}" if first == last else f"overs {first} to {last}"
    s = f"In the most recent play ({span}), {ctx['now']['batting_team']} scored {runs} runs and lost {plural(wk, 'wicket')}"
    s += f", reaching {ov[-1]['score_after']}."
    return s


def s_performers(ctx: dict) -> str | None:
    p, bits = ctx["performers"], []
    if "top_scorer" in p:
        t = p["top_scorer"]
        bits.append(f"{t['name']} leads the runs with {t['runs']} from {t['balls']} balls")
    if "top_wicket_taker" in p:
        t = p["top_wicket_taker"]
        bits.append(f"{t['name']} leads the bowlers with {plural(t['wickets'], 'wicket')} for {t['runs']}")
    if "best_strike_rate" in p and p["best_strike_rate"]["name"] != p.get("top_scorer", {}).get("name"):
        t = p["best_strike_rate"]
        bits.append(f"{t['name']} has the best strike rate ({t['strike_rate']})")
    if "best_economy" in p:
        t = p["best_economy"]
        bits.append(f"{t['name']} has the best economy ({t['economy']} over {t['overs']} overs)")
    return (names(bits) + ".") if bits else None


def s_current_players(ctx: dict) -> str | None:
    n = ctx["now"]
    if n["innings_finished"]:
        return None
    bits = []
    if n["current_batters"]:
        bits.append(f"at the crease: {names(n['current_batters'])}")
    if n["current_bowler"]:
        bits.append(f"{n['current_bowler']} is bowling")
    return (", ".join(bits)[0].upper() + ", ".join(bits)[1:] + ".") if bits else None


# ---- assembly -------------------------------------------------------------
def fallback_recap(ctx: dict) -> list[str]:
    length, focus = ctx["length"], ctx["focus"]
    innings = ctx["innings"]
    cur = innings[-1]
    sit = s_situation(ctx)
    detailed = length == "detailed"
    paras: list[str | None] = [sit]

    if focus == "everything":
        if length == "quick":
            paras += [s_performers(ctx), s_turning(ctx, 1), s_recent(ctx)]
        else:
            for inn in (innings if detailed else innings[-2:]):
                paras += [s_start(ctx, inn), s_phases(inn) if detailed else None, s_partnerships(inn), s_wickets(inn, 8 if detailed else 4),
                          s_batting(inn, 3 if detailed else 2), s_bowling(inn, 3 if detailed else 2)]
            paras += [s_turning(ctx, 4 if detailed else 2), s_milestones(ctx, 6 if detailed else 2), s_recent(ctx), s_current_players(ctx)]
    elif focus == "players":
        for inn in (innings if length != "quick" else [cur]):
            paras += [s_batting(inn, 4 if detailed else 3), s_bowling(inn, 3 if detailed else 2)]
        paras += [s_performers(ctx), s_milestones(ctx, 3) if length != "quick" else None]
    elif focus == "wickets":
        for inn in (innings if length != "quick" else [cur]):
            paras += [s_wickets(inn, 10 if detailed else 5)]
        paras += [s_turning(ctx, 5 if detailed else 3 if length == "standard" else 1)]
        paras += [s_bowling(cur, 3)] if length != "quick" else []
    elif focus == "milestones":
        paras += [s_milestones(ctx, 10 if detailed else 6 if length == "standard" else 3)]
        for inn in (innings if length != "quick" else [cur]):
            paras += [s_partnerships(inn)]
    else:  # situation
        paras += [s_current_players(ctx), s_recent(ctx)]
        if length != "quick":
            paras += [s_turning(ctx, 2), s_partnerships(cur)]
        if detailed:
            paras += [s_start(ctx, cur), s_batting(cur, 3), s_bowling(cur, 3)]

    paras = [p for p in paras if p]
    limit = WORD_TARGET[length] * 1.35
    out, words = [], 0
    for p in paras:
        w = len(p.split())
        if out and words + w > limit:
            continue
        out.append(p)
        words += w
    return out


# ---- event explanations ---------------------------------------------------
def fallback_event_explanation(facts: dict, title: str) -> str:
    t = facts["type"]
    team = facts["team"]
    nxt = facts.get("next_overs")
    after = ""
    if nxt:
        after = f" In the next {nxt['balls']} balls {team} scored {nxt['runs']} and lost {plural(nxt['wickets'], 'wicket')}."
    tp = facts.get("turning_point")
    tp_txt = f" It sits inside a flagged turning point ({tp['label'].lower()}, rank {tp['rank']})." if tp else ""
    phase = f" in the {facts['phase']}" if facts.get("phase") else ""
    if t == "wicket":
        s = f"{facts['dismissed']} was out ({facts['kind']}) for {facts['batter_runs']} off {facts['batter_balls']} balls{phase}, " \
            f"the {ordinal(facts['wicket_no'])} wicket, leaving {team} on {facts['score_after']}."
        p = facts.get("partnership_ended")
        if p:
            s += f" It ended a {p['runs']}-run partnership between {names(p['batters'])} ({p['balls']} balls)."
        if facts["wickets_last_two_overs"] >= 2:
            s += f" {plural(facts['wickets_last_two_overs'], 'wicket')} have fallen in the last two overs, adding to the pressure."
        return s + after + tp_txt
    if t in ("six", "four"):
        s = f"{facts['batter']} took {'six' if t == 'six' else 'four'} off {facts['bowler']}{phase}, moving to {facts['batter_runs']}. " \
            f"That over has gone for {facts['over_runs_so_far']} so far and the score is {facts['score_after']}."
        if facts["innings_run_rate_before"]:
            s += f" The innings run rate before this ball was {facts['innings_run_rate_before']}."
        return s + after + tp_txt
    if t == "milestone" and facts.get("milestone"):
        return facts["milestone"]["detail"] + f" Score at the time: {facts['score_after']}{phase}." + after + tp_txt
    if t == "big_over":
        return f"This over was expensive: the last two overs produced {facts['runs_last_two_overs']} runs, taking {team} to {facts['score_after']}." + after + tp_txt
    if t == "maiden":
        return f"A maiden over: the bowler conceded no runs, and {team} are {facts['score_after']}." + after + tp_txt
    if t == "innings_break":
        return f"The innings closed on {facts['score_after']}."
    if t == "phase":
        return f"{team} are {facts['score_after']} at this stage{phase}."
    return f"{title}. Score: {facts['score_after']}." + tp_txt


# ---- player insights ------------------------------------------------------
def batting_insight(s: dict) -> str | None:
    b = s["batting"]
    if not b or b["balls"] == 0:
        return None
    t = f"{s['name']} has scored {b['runs']} runs from {b['balls']} balls"
    if b["fours"] or b["sixes"]:
        t += f", including {plural(b['fours'], 'four')} and {plural(b['sixes'], 'six')}"
    if b["strike_rate"] is not None:
        t += f". Strike rate: {b['strike_rate']}"
    if b["dismissals"] == 0 and b["innings"]:
        t += " (not out)"
    return t + "."


def bowling_insight(s: dict) -> str | None:
    b = s["bowling"]
    if not b or b["legal_balls"] == 0:
        return None
    t = f"{s['name']} bowled {b['overs']} overs, taking {plural(b['wickets'], 'wicket')} for {b['runs']} runs (economy {b['economy']}"
    t += f", {plural(b['maidens'], 'maiden')}" if b["maidens"] else ""
    return t + ")."
