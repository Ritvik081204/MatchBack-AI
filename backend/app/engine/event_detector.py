"""Builds the chronological match timeline and the measured facts behind any single event."""
from __future__ import annotations

from .match_processor import MatchData, overs_str, rate
from .statistics import dismissal_text, over_by_over

BIG_OVER = {"T20": 14, "ODI": 12, "TEST": 10}
CATEGORY = {"wicket": "wicket", "six": "boundary", "four": "boundary", "milestone": "milestone", "drs": "other",
            "maiden": "other", "big_over": "other", "innings_break": "other", "innings_start": "other", "phase": "other"}
MILESTONE_IMPORTANCE = {"bat_30": 35, "bat_50": 70, "bat_100": 92, "bat_150": 95, "bat_200": 97, "bat_250": 98, "bat_300": 99,
                        "bowl_3w": 60, "bowl_4w": 75, "bowl_5w": 88, "bowl_10w_match": 98}


def build_timeline(md: MatchData, milestones: list[dict], turning_points: list[dict]) -> list[dict]:
    d = md.deliveries
    bpo = md.balls_per_over
    events: list[dict] = []
    bat: dict[tuple, dict] = {}

    def add(r, etype: str, title: str, desc: str, importance: int, players: list[str], runs: int | None = None, **extra):  # noqa: ANN001
        events.append({
            "id": f"ev-{r.seq}-{etype}-{len(events)}", "seq": int(r.seq), "innings_no": int(r.innings_no),
            "over": f"{r.over_no}.{r.ball_no}", "over_no": int(r.over_no) + 1, "ball": int(r.ball_no), "type": etype,
            "category": CATEGORY[etype], "team": r.batting_team, "players": players, "runs": runs, "title": title,
            "description": desc, "importance": importance, "score_after": f"{int(r.team_runs)}/{int(r.team_wkts)}",
            "turning_point": None, **extra,
        })

    wk_by_seq = {s: g for s, g in md.wickets.groupby("seq")}
    inn_last = md.innings_last_seq
    for r in d.itertuples():
        key = (r.innings_no, r.batter)
        b = bat.setdefault(key, {"runs": 0, "balls": 0})
        b["runs"] += int(r.batter_runs); b["balls"] += int(r.faced)
        if r.ball_no == 1 and r.over_no == 0 and r.ball_idx == 1:
            meta = md.innings_meta(r.innings_no)
            tgt = meta.get("target_runs") or (None)
            extra = f", chasing {tgt}" if tgt and md.format != "TEST" else ""
            add(r, "innings_start", f"{r.batting_team} start their innings{extra}",
                f"Innings {r.innings_no}: {r.batting_team} face {r.bowler} first.", 25, [])
        if r.is_six:
            add(r, "six", f"SIX! {r.batter}", f"{r.batter} hits {r.bowler} for six ({b['runs']} off {b['balls']}).", 30,
                [r.batter, r.bowler], 6)
        elif r.is_four:
            add(r, "four", f"FOUR! {r.batter}", f"{r.batter} finds the boundary off {r.bowler} ({b['runs']} off {b['balls']}).", 15,
                [r.batter, r.bowler], 4)
        if r.is_wicket:
            for w in wk_by_seq[r.seq].itertuples():
                out_stats = bat.get((r.innings_no, w.player_out), {"runs": 0, "balls": 0})
                how = dismissal_text(w.kind, w.bowler, list(w.fielders))
                imp = 55 + (15 if out_stats["runs"] >= 50 else 8 if out_stats["runs"] >= 30 else 0) + (6 if w.wicket_no <= 3 else 0)
                add(r, "wicket", f"WICKET! {w.player_out} {how}",
                    f"{w.player_out} is out ({how}) for {out_stats['runs']} off {out_stats['balls']} balls. "
                    f"{r.batting_team} {int(r.team_runs)}/{int(r.team_wkts)}.", min(imp, 90), [w.player_out, w.bowler], int(r.total),
                    wicket_kind=w.kind, wicket_no=int(w.wicket_no))
        if r.has_review:
            rv = r.review
            add(r, "drs", f"DRS review by {rv.get('by', 'a team')}",
                f"Review ({rv.get('type', 'decision')}): {rv.get('decision', 'outcome unknown')}"
                + (f" - batter {rv['batter']}" if rv.get("batter") else "") + ".", 35, [rv["batter"]] if rv.get("batter") else [])
        # innings break / close
        if r.seq == inn_last.get(r.innings_no) and md.innings_finished(r.innings_no):
            meta = md.innings_meta(r.innings_no)
            word = "declare" if meta.get("declared") else "finish"
            add(r, "innings_break", f"Innings break: {r.batting_team} {word} on {int(r.team_runs)}/{int(r.team_wkts)}",
                f"{r.batting_team} {word} their innings on {int(r.team_runs)}/{int(r.team_wkts)} after {overs_str(int(r.legal_balls), bpo)} overs.",
                50, [])

    # over-level events
    for o in over_by_over(md):
        r = d[d.seq == o["end_seq"]].iloc[0]
        if o["complete"] and o["runs"] >= BIG_OVER[md.format]:
            add(r, "big_over", f"Big over: {o['runs']} runs",
                f"Over {o['over']} cost {o['runs']} runs ({o['fours']} fours, {o['sixes']} sixes) off {' / '.join(o['bowlers'])}.", 55,
                o["bowlers"], o["runs"])
        if o["maiden"] and md.format != "TEST":
            add(r, "maiden", f"Maiden over by {o['bowlers'][0]}", f"{o['bowlers'][0]} bowls a maiden in over {o['over']}.", 40, o["bowlers"], 0)
        pp_end = {"T20": 6, "ODI": 10}.get(md.format)
        if pp_end and o["over"] == pp_end and o["complete"]:
            add(r, "phase", f"End of the {'powerplay' if md.format == 'T20' else 'first 10 overs'}",
                f"{o['team']} are {o['cum_runs']}/{o['cum_wickets']} after {pp_end} overs (run rate {o['run_rate']}).", 30, [])

    for m in milestones:
        r = d[d.seq == m["seq"]].iloc[0]
        add(r, "milestone", m["title"], m["detail"], MILESTONE_IMPORTANCE.get(m["kind"], 65 if m["category"] == "partnership" else 45),
            m["players"], None, milestone_id=m["id"], badge=m["badge"], milestone_kind=m["kind"], superseded=m.get("superseded", False))

    for tp in turning_points:
        for e in events:
            # only events that ARE the turning point carry the flag: wickets / big overs always, boundaries only for boundary-driven kinds
            kinds = ("wicket", "big_over") + (("six", "four") if tp["kind"] in ("boundary_burst", "high_scoring_over", "acceleration") else ())
            if e["innings_no"] == tp["innings_no"] and tp["start_seq"] <= e["seq"] <= tp["end_seq"] and e["type"] in kinds:
                e["importance"] = min(100, e["importance"] + 8)
                e["turning_point"] = tp["id"]
    order = {"innings_start": 0, "six": 2, "four": 2, "drs": 3, "wicket": 4, "milestone": 5, "big_over": 6, "maiden": 6, "phase": 7, "innings_break": 8}
    events.sort(key=lambda e: (e["seq"], order.get(e["type"], 5)))
    return events


def event_facts(md: MatchData, event: dict, milestones: list[dict], turning_points: list[dict]) -> dict:
    """Measured context for one event: only data at/before the cut-off. Basis for 'why it mattered'."""
    d = md.innings_df(event["innings_no"])
    seq = event["seq"]
    bpo = md.balls_per_over
    ball = d[d.seq == seq].iloc[0]
    before = d[d.seq < seq]
    inn_rr = rate(int(before.total.sum()), int(before.legal.sum()), bpo)
    last_over = d[(d.legal_balls > ball.legal_balls - bpo * 2) & (d.seq <= seq)]
    facts: dict = {
        "type": event["type"], "team": event["team"], "over": event["over"], "score_after": event["score_after"],
        "innings_run_rate_before": inn_rr, "runs_last_two_overs": int(last_over.total.sum()),
        "wickets_last_two_overs": int(last_over.n_wickets.sum()),
        "phase": _phase(md, int(ball.over_no)),
    }
    after = d[d.seq > seq].head(bpo * 2)
    if int(after.legal.sum()) >= bpo:
        facts["next_overs"] = {"balls": int(after.legal.sum()), "runs": int(after.total.sum()), "wickets": int(after.n_wickets.sum())}
    if event["type"] == "wicket":
        w = md.wickets[(md.wickets.seq == seq)].iloc[0]
        parts = [p for p in _parts(md) if p["innings_no"] == event["innings_no"] and p["end_seq"] == seq]
        batter = d[(d.seq <= seq) & (d.batter == w.player_out)]
        facts.update({
            "dismissed": w.player_out, "kind": w.kind, "bowler": w.bowler, "bowler_credited": bool(w.bowler_credited),
            "batter_runs": int(batter.batter_runs.sum()), "batter_balls": int(batter.faced.sum()),
            "wicket_no": int(w.wicket_no),
            "partnership_ended": ({"runs": parts[0]["runs"], "balls": parts[0]["balls"], "batters": parts[0]["batters"]} if parts else None),
        })
    elif event["type"] in ("six", "four"):
        over = d[(d.over_no == ball.over_no) & (d.seq <= seq)]
        facts.update({"batter": ball.batter, "bowler": ball.bowler, "over_runs_so_far": int(over.total.sum()),
                      "boundaries_in_over_so_far": int(over.is_four.sum() + over.is_six.sum()),
                      "batter_runs": int(d[(d.seq <= seq) & (d.batter == ball.batter)].batter_runs.sum())})
    elif event["type"] in ("milestone", "big_over", "maiden", "phase", "innings_break", "innings_start", "drs"):
        m = next((x for x in milestones if x["id"] == event.get("milestone_id")), None)
        if m:
            facts["milestone"] = {"kind": m["kind"], "stats": m["stats"], "players": m["players"], "detail": m["detail"]}
    tp = next((t for t in turning_points if t["id"] == event.get("turning_point")), None)
    if tp:
        facts["turning_point"] = {"kind": tp["kind"], "label": tp["label"], "rank": tp["rank"], "explanation": tp["explanation"]}
    return facts


def _phase(md: MatchData, over_no: int) -> str | None:
    if md.format == "T20":
        return "powerplay" if over_no < 6 else "middle overs" if over_no < 15 else "death overs"
    if md.format == "ODI":
        return "first powerplay" if over_no < 10 else "middle overs" if over_no < 40 else "death overs"
    return None


def _parts(md: MatchData) -> list[dict]:
    from .statistics import partnerships
    return partnerships(md)
