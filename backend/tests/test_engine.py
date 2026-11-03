import json

import pytest

from app.data.cricsheet_parser import infer_format, outcome_text, parse_match
from app.data.data_validator import ValidationError
from app.engine.match_processor import overs_str, situation
from app.engine.milestone_detector import detect_milestones
from app.engine.statistics import batting_card, bowling_card, highlights, over_by_over, partnerships, player_stats
from app.engine.turning_points import detect_turning_points

from conftest import SAMPLES, ball, make_md, md_from_sample, raw_match, wk


# ---------------------------------------------------------------- parsing / validation
def test_parses_real_sample_and_counts_deliveries():
    raw = json.loads((SAMPLES / "1550716.json").read_text(encoding="utf8"))
    pm = parse_match(raw, "1550716")
    expected = sum(len(o["deliveries"]) for i in raw["innings"] for o in i["overs"])
    assert len(pm.deliveries) == expected
    assert pm.format == "ODI" and pm.teams == raw["info"]["teams"]
    assert [d["seq"] for d in pm.deliveries] == list(range(expected))


def test_extras_are_split_by_kind():
    pm = parse_match(raw_match([[ball(extras={"wides": 2}), ball(extras={"noballs": 1}, runs=4), ball(extras={"byes": 1}),
                                 ball(extras={"legbyes": 2}), ball(extras={"penalty": 5})]]), "x")
    d = pm.deliveries
    assert (d[0]["wides"], d[1]["noballs"], d[2]["byes"], d[3]["legbyes"], d[4]["penalty"]) == (2, 1, 1, 2, 5)
    assert d[1]["batter_runs"] == 4 and d[1]["extras"] == 1 and d[1]["total"] == 5


@pytest.mark.parametrize("bad", [{}, {"info": {"teams": ["A"], "dates": ["2026-01-01"]}, "innings": []},
                                 {"info": {"teams": ["A", "B"], "dates": []}, "innings": [{}]},
                                 {"info": {"teams": ["A", "B"], "dates": ["2026-01-01"]}, "innings": []}])
def test_invalid_files_are_rejected(bad):
    with pytest.raises(ValidationError):
        parse_match(bad, "bad")


def test_missing_optional_metadata_is_tolerated_and_reported():
    raw = raw_match([[ball(runs=1)] * 6])
    for k in ("venue", "toss", "outcome", "match_type", "overs"):
        raw["info"].pop(k, None)
    pm = parse_match(raw, "m")
    md_ = make_md([[ball(runs=1)] * 6])
    assert any("venue" in w for w in pm.warnings) and any("squad" in w for w in pm.warnings)
    assert md_.deliveries.batter_runs.sum() == 6
    assert infer_format({"overs": 20}) == "T20" and infer_format({"overs": 50}) == "ODI" and infer_format({}) == "TEST"


def test_delivery_without_non_striker_still_processes():
    raw = raw_match([[ball(runs=1)] * 6])
    for o in raw["innings"][0]["overs"]:
        for d in o["deliveries"]:
            d.pop("non_striker", None)
    md = from_parsed_raw(raw)
    assert md.deliveries.total.sum() == 6 and md.deliveries.non_striker.isna().all()


def from_parsed_raw(raw):
    from app.engine.match_processor import from_parsed
    return from_parsed(parse_match(raw, "m"))


def test_outcome_text_variants():
    assert outcome_text({"outcome": {"winner": "A", "by": {"runs": 1}}}) == "A won by 1 run"
    assert outcome_text({"outcome": {"winner": "A", "by": {"wickets": 3}}}) == "A won by 3 wickets"
    assert outcome_text({"outcome": {"winner": "A", "by": {"innings": 1, "runs": 31}}}) == "A won by an innings and 31 runs"
    assert outcome_text({"outcome": {"result": "tie"}}) == "Match tied"
    assert outcome_text({"outcome": {"result": "no result"}}) == "No result"
    assert outcome_text({}) == "Result not recorded"


# ---------------------------------------------------------------- ball-by-ball rules
def sample_innings():
    """Over 0: 1, W(wide)+0 off bat, 4, nb+2 off bat, dot, bye 1, 6, leg-bye 2, then wicket on last legal ball."""
    return [[
        ball("A", "B", "X", 1),
        ball("B", "A", "X", 0, {"wides": 1}),               # illegal, not faced
        ball("A", "B", "X", 4),
        ball("A", "B", "X", 2, {"noballs": 1}),             # illegal, faced, 2 off the bat
        ball("A", "B", "X", 0),
        ball("A", "B", "X", 0, {"byes": 1}),                # legal, bye
        ball("A", "B", "X", 6),
        ball("A", "B", "X", 0, {"legbyes": 2}),             # legal, leg-bye
        ball("A", "B", "X", 0, wicket=wk("bowled", "A")),   # 7th legal? -> next over
    ]]


def test_batter_runs_exclude_extras_and_wides_are_not_faced():
    md = make_md(sample_innings())
    a = batting_card(md, 1)["batters"][0]
    # A: 1 + 4 + (nb 2) + 0 + 0 + 6 + 0 + 0 = 13 off bat; balls faced = all except the wide (B faced the wide) -> 7
    assert a["name"] == "A" and a["runs"] == 13
    assert a["balls"] == 8  # A faced 8 deliveries (the no-ball counts, the wide was faced by nobody)
    assert a["fours"] == 1 and a["sixes"] == 1
    b = next(x for x in batting_card(md, 1)["batters"] if x["name"] == "B")
    assert b["runs"] == 0 and b["balls"] == 0  # wide is not a ball faced


def test_legal_deliveries_and_overs_notation():
    md = make_md(sample_innings())
    d = md.deliveries
    assert list(d.legal) == [True, False, True, False, True, True, True, True, True]
    assert d.legal.sum() == 7
    assert overs_str(7, 6) == "1.1" and overs_str(36, 6) == "6.0"
    assert batting_card(md, 1)["total"]["overs"] == "1.1"


def test_total_equals_batter_runs_plus_extras():
    md = make_md(sample_innings())
    card = batting_card(md, 1)
    assert card["total"]["runs"] == sum(b["runs"] for b in card["batters"]) + card["extras"]["total"] == 13 + 1 + 1 + 1 + 2
    assert card["extras"] == {"total": 5, "wides": 1, "noballs": 1, "byes": 1, "legbyes": 2, "penalty": 0}


def test_bowler_conceded_excludes_byes_and_legbyes_but_includes_wides_and_noballs():
    md = make_md(sample_innings())
    x = bowling_card(md, 1)["bowlers"][0]
    # bat 13 + wide 1 + noball 1 = 15; byes(1) and legbyes(2) not charged
    assert x["runs"] == 15 and x["wickets"] == 1 and x["legal_balls"] == 7 and x["overs"] == "1.1"
    assert x["economy"] == round(15 * 6 / 7, 2) and x["average"] == 15.0


def test_maiden_requires_six_legal_balls_and_no_bowler_runs():
    clean_maiden = [ball() for _ in range(6)] + [ball(runs=1)] * 6
    with_wide = [ball(), ball(extras={"wides": 1})] + [ball() for _ in range(5)] + [ball(runs=1)] * 6
    with_bye = [ball(extras={"byes": 4})] + [ball() for _ in range(5)] + [ball(runs=1)] * 6
    assert over_by_over(make_md([clean_maiden]))[0]["maiden"] is True
    assert over_by_over(make_md([with_wide]))[0]["maiden"] is False   # wide is charged to the bowler
    assert over_by_over(make_md([with_bye]))[0]["maiden"] is True     # byes are not
    assert bowling_card(make_md([clean_maiden]), 1)["bowlers"][0]["maidens"] == 1


@pytest.mark.parametrize("kind,credited", [("bowled", True), ("lbw", True), ("caught", True), ("stumped", True),
                                           ("caught and bowled", True), ("hit wicket", True), ("run out", False),
                                           ("obstructing the field", False), ("timed out", False)])
def test_bowler_wicket_credit_by_dismissal_type(kind, credited):
    md = make_md([[ball(wicket=wk(kind, "A", ["F"] if kind in ("caught", "run out", "stumped") else None))] + [ball(runs=1)] * 5])
    assert bowling_card(md, 1)["bowlers"][0]["wickets"] == int(credited)
    assert md.deliveries.team_wkts.iloc[-1] == 1  # still a team wicket


def test_retired_hurt_is_not_a_team_wicket():
    md = make_md([[ball(wicket=wk("retired hurt", "A"))] + [ball(runs=1)] * 5])
    assert md.deliveries.n_wickets.sum() == 0
    assert bowling_card(md, 1)["bowlers"][0]["wickets"] == 0
    assert batting_card(md, 1)["batters"][0]["out"] is False


def test_dismissal_text_and_fielding_stats():
    balls = [ball("A", "B", "X", 0, wicket=wk("caught", "A", ["F1"])), ball("C", "B", "X", 0, wicket=wk("run out", "B", ["F2", "F3"])),
             ball("C", "D", "X", 0, wicket=wk("stumped", "C", ["WK"])), ball("E", "D", "Y", 0, wicket=wk("caught and bowled", "E"))]
    md = make_md([balls + [ball("D", "F", "Y", 1)] * 2])
    texts = {b["name"]: b["dismissal"] for b in batting_card(md, 1)["batters"]}
    assert texts["A"] == "c F1 b X" and texts["B"] == "run out (F2 / F3)" and texts["C"] == "st WK b X" and texts["E"] == "c & b Y"
    stats = {s["name"]: s["fielding"] for s in player_stats(md)}
    assert stats["F1"]["catches"] == 1 and stats["WK"]["stumpings"] == 1 and stats["F2"]["run_outs"] == 1 and stats["Y"]["catches"] == 1


def test_non_boundary_four_is_not_a_boundary():
    md = make_md([[ball(runs=4, boundary_run=True), ball(runs=4), ball(runs=6)] + [ball()] * 3])
    assert int(md.deliveries.is_four.sum()) == 1 and int(md.deliveries.is_six.sum()) == 1
    assert batting_card(md, 1)["batters"][0]["runs"] == 14


# ---------------------------------------------------------------- partnerships
def test_partnership_runs_include_extras_and_split_at_wickets():
    balls = ([ball("A", "B", "X", 1)] * 4 + [ball("A", "B", "X", 0, {"wides": 2})] + [ball("B", "A", "X", 4)] * 1   # 4+2+4 = 10
             + [ball("A", "B", "X", 0, wicket=wk("bowled", "A"))]
             + [ball("C", "B", "X", 2)] * 3 + [ball("C", "B", "X", 0, {"legbyes": 1})] * 1)                       # 7
    md = make_md([balls])
    ps = partnerships(md)
    assert [(p["runs"], p["wicket_no"], p["unbroken"]) for p in ps] == [(10, 1, False), (7, 2, True)]
    assert set(ps[0]["batters"]) == {"A", "B"} and set(ps[1]["batters"]) == {"C", "B"}
    assert ps[0]["contributions"]["A"]["runs"] == 4 and ps[0]["contributions"]["B"]["runs"] == 4
    assert ps[0]["balls"] == 6  # wide not legal


# ---------------------------------------------------------------- milestones
def test_batting_milestones_are_detected_once_with_correct_balls():
    md = make_md([[ball("A", "B", "X", 6)] * 18])  # 108 runs off 18 balls
    ms = [m for m in detect_milestones(md) if m["category"] == "batting"]
    kinds = [m["kind"] for m in ms]
    assert kinds == ["bat_30", "bat_50", "bat_100"] and len(set(kinds)) == 3
    fifty = next(m for m in ms if m["kind"] == "bat_50")
    assert fifty["stats"]["runs"] == 54 and fifty["stats"]["balls"] == 9 and fifty["over"] == "1.3"
    assert [m["superseded"] for m in ms] == [True, True, False]   # only the highest step is the headline


def test_team_partnership_and_bowling_milestones():
    balls = [ball("A", "B", "X", 6)] * 10 + [ball("C", "D", "Y", 0, wicket=wk("bowled", "C")), ball("E", "D", "Y", 0, wicket=wk("bowled", "E")),
                                             ball("F", "D", "Y", 0, wicket=wk("lbw", "F"))]
    md = make_md([balls])
    ms = detect_milestones(md)
    cats = {(m["category"], m["kind"]) for m in ms}
    assert ("team", "team_50") in cats and ("team", "team_100") not in cats
    assert ("partnership", "partnership_50") in cats
    three = next(m for m in ms if m["kind"] == "bowl_3w")
    assert three["players"] == ["Y"] and three["stats"]["wickets"] == 3 and three["stats"]["runs"] == 0


def test_no_career_or_historical_fastest_claims():
    md = make_md([[ball("A", "B", "X", 6)] * 18])
    text = json.dumps(detect_milestones(md)).lower()
    assert "career" not in text and "fastest-ever" not in text and "record" not in text


def test_ten_wicket_match_haul_in_test():
    one_inn = [ball("A", "B", "Z", 0, wicket=wk("bowled", n)) for n in "ABCDE"]
    md = make_md([one_inn, one_inn, one_inn, one_inn], match_type="Test", overs=None)
    ms = [m for m in detect_milestones(md) if m["kind"] == "bowl_10w_match"]
    assert len(ms) == 1 and ms[0]["players"] == ["Z"]
    assert not [m for m in detect_milestones(make_md([one_inn, one_inn], "T20")) if m["kind"] == "bowl_10w_match"]


# ---------------------------------------------------------------- turning points
def collapse_innings():
    steady = [ball("A", "B", "X", 2)] * 24                                         # 48 runs, one long stand
    fall = [ball("A", "B", "X", 0, wicket=wk("bowled", "A")), ball("C", "B", "X", 0, wicket=wk("caught", "C", ["F"])),
            ball("D", "B", "X", 0, wicket=wk("lbw", "D"))] + [ball("E", "B", "X", 0)] * 9
    return steady + fall


def test_collapse_after_strong_partnership_is_detected_and_ranked():
    tps = detect_turning_points(make_md([collapse_innings()]))
    top = max(tps, key=lambda t: t["score"])
    assert top["kind"] == "collapse" and top["rank"] == 1
    f = top["facts"]
    assert f["wickets"] == 3 and f["partnership_ended"]["runs"] == 48
    assert "3 wickets" in top["explanation"] and "48-run partnership" in top["explanation"]
    assert 0 < top["score"] <= 100


def test_a_lone_wicket_is_not_a_turning_point():
    balls = [ball("A", "B", "X", 1)] * 8 + [ball("A", "B", "X", 0, wicket=wk("bowled", "A"))] + [ball("C", "B", "X", 1)] * 12
    assert detect_turning_points(make_md([balls])) == []


def test_high_scoring_over_threshold_is_format_specific():
    ov = [ball("A", "B", "X", 6)] * 3 + [ball("A", "B", "X", 1)] * 3        # 21 runs
    quiet = [ball("A", "B", "X", 1)] * 12
    t20 = detect_turning_points(make_md([quiet + ov + quiet]))
    assert any(t["kind"] == "high_scoring_over" and t["facts"]["runs"] == 21 for t in t20)


def test_turning_points_never_use_future_data():
    md = make_md([collapse_innings()])
    early = md.upto(23)  # before the wickets
    assert not [t for t in detect_turning_points(early) if t["kind"] in ("collapse", "wicket_cluster")]


# ---------------------------------------------------------------- formats / situation
def test_t20_chase_situation_and_required_rate():
    first = [ball("A", "B", "X", 1)] * 60 + [ball("A", "B", "X", 0)] * 60      # 60 runs, 20 overs
    second = [ball("P", "Q", "Z", 1)] * 12 + [ball("P", "Q", "Z", 0)] * 2        # 2 overs, 12 runs, then 2 balls we cut off
    md = make_md([first, second])
    implied = situation(md.upto(md.max_seq - 2))
    assert implied["target"] == 61                                               # no explicit target: first innings + 1
    md = make_md([first, second], target=61)
    s = situation(md.upto(md.max_seq - 2))
    assert s["runs_needed"] == 49 and s["balls_remaining"] == 108 and s["required_rate"] == round(49 * 6 / 108, 2)
    assert s["run_rate"] == 6.0 and s["status"] == "Beta need 49 from 108 balls"
    assert s["current_batters"] == ["P", "Q"] and s["current_bowler"] == "Z"


def test_odi_limit_and_phases_use_fifty_overs():
    md = make_md([[ball("A", "B", "X", 1)] * 300], "ODI", overs=50)
    from app.engine.statistics import phases
    ph = phases(md, 1)
    assert [p["name"] for p in ph] == ["Powerplay", "Middle overs", "Death overs"] and sum(p["runs"] for p in ph) == 300
    assert ph[0]["to_over"] == 10 and ph[1]["from_over"] == 11


def test_test_match_lead_and_no_phases():
    inn = [ball("A", "B", "X", 1)] * 60
    md = make_md([inn, [ball("P", "Q", "Y", 1)] * 30, inn], "Test", overs=None)
    s = situation(md.upto(60 + 30 + 20 - 1))   # sequence numbers are 0-based: 20 balls of the 3rd innings
    assert s["lead"] == (60 + 20) - 30 and "lead by 50" in s["status"]
    from app.engine.statistics import phases
    assert phases(md, 1) == []


def test_cutoff_hides_future_and_result():
    md = md_from_sample("1550716")
    cut = md.upto(300)
    assert cut.cutoff_seq == 300 and cut.complete is False and cut.deliveries.seq.max() == 300
    s = situation(cut)
    assert "won by" not in s["status"]
    full = situation(md)
    assert "Pakistan won by 1 wicket" in full["status"]


# ---------------------------------------------------------------- highlights
def test_highlights_respect_minimum_thresholds():
    balls = ([ball("A", "B", "X", 6)] * 3                                  # 18 off 3: huge SR but under 12 balls
             + [ball("C", "B", "X", 1)] * 12 + [ball("C", "B", "Y", 1)] * 3)
    md = make_md([balls + [ball("C", "B", "Y", 0)] * 6])
    h = highlights(md, player_stats(md))
    assert h["best_strike_rate"]["name"] == "C"          # A faced only 3 balls (<12)
    assert h["top_scorer"]["name"] == "A"
    assert h["best_economy"] is None or h["best_economy"]["name"] in ("X", "Y")


# ---------------------------------------------------------------- real-data reconciliation
@pytest.mark.parametrize("mid", ["1550716", "1535465", "1525659", "1528722", "1544603"])
def test_scorecard_totals_reconcile_with_raw_cricsheet(mid):
    raw = json.loads((SAMPLES / f"{mid}.json").read_text(encoding="utf8"))
    md = md_from_sample(mid)
    for n, inn in enumerate(raw["innings"], start=1):
        total = sum(x["runs"]["total"] for o in inn["overs"] for x in o["deliveries"])
        card = batting_card(md, n)
        assert card["total"]["runs"] == total == sum(b["runs"] for b in card["batters"]) + card["extras"]["total"]
        wkts = sum(len(x.get("wickets", [])) for o in inn["overs"] for x in o["deliveries"])
        assert card["total"]["wickets"] <= wkts <= card["total"]["wickets"] + 2
        bowl_runs = sum(b["runs"] for b in bowling_card(md, n)["bowlers"])
        assert bowl_runs == total - card["extras"]["byes"] - card["extras"]["legbyes"] - card["extras"]["penalty"]
