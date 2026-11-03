import json

import pytest

from app.ai import llm_service
from app.ai.context_builder import build_context
from app.ai.event_explainer import explain_event
from app.ai.fallback_generator import ordinal, plural
from app.ai.insight_generator import player_insights
from app.ai.llm_service import grounding_violations
from app.ai.question_answering import answer_question, classify, find_player
from app.ai.summary_generator import generate_recap
from app.analysis import Analysis

from conftest import ball, make_analysis, md_from_sample, wk


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    """Tests must pass with no Ollama present - that is the contract of the fallback."""
    monkeypatch.setattr(llm_service.llm, "status", lambda force=False: {"available": False})


def small_match(cutoff=None):
    first = ([ball("Kohli", "Rohit", "Starc", 4)] * 3 + [ball("Kohli", "Rohit", "Starc", 6)] * 3 +
             [ball("Rohit", "Kohli", "Cummins", 1)] * 6 +
             [ball("Kohli", "Rohit", "Starc", 0, wicket=wk("caught", "Kohli", ["Smith"]))] + [ball("Pant", "Rohit", "Starc", 1)] * 5)
    second = [ball("Warner", "Smith", "Bumrah", 2)] * 6 + [ball("Warner", "Smith", "Shami", 0, wicket=wk("bowled", "Warner"))] + [ball("Smith", "Head", "Shami", 1)] * 5
    return make_analysis([first, second], teams=("India", "Australia"), target=63, cutoff=cutoff)


def test_recap_is_generated_without_llm_and_is_grounded():
    a = small_match(cutoff=25)   # 18 balls of innings 1, then 8 balls of the chase: Australia 13/1
    r = generate_recap(a, "quick", "everything")
    text = " ".join(r["paragraphs"])
    assert r["engine"] == "rule-based" and r["note"]
    assert "Australia are 13/1 after 1.2 overs" in text
    assert "chasing 63" in text and "need 50" in text     # 63 - 13
    assert "won by" not in text                           # in progress: no result leaked
    assert r["generated_ms"] < 2000


@pytest.mark.parametrize("length", ["quick", "standard", "detailed"])
@pytest.mark.parametrize("focus", ["everything", "players", "wickets", "milestones", "situation"])
def test_every_length_and_focus_produces_text(length, focus):
    r = generate_recap(small_match(), length, focus)
    assert r["paragraphs"] and r["word_count"] > 10


def test_recap_length_ordering():
    a = md_analysis("1550716", 400)
    q, s, d = (generate_recap(a, k)["word_count"] for k in ("quick", "standard", "detailed"))
    assert q < s < d
    assert q < 140      # roughly "30 seconds" of reading


def md_analysis(name, cutoff=None):
    return Analysis(md_from_sample(name), cutoff)


def test_context_is_compact_and_has_no_raw_deliveries():
    a = md_analysis("1525659", 1500)   # Test match, thousands of deliveries
    ctx = build_context(a, "standard", "everything")
    blob = json.dumps(ctx)
    assert len(blob) < 12000 and len(a.md.deliveries) > 1000
    assert "batter_runs" not in blob and "non_striker" not in blob
    assert ctx["match"]["result"] is None and "final result is unknown" in ctx["match"]["note"]


def test_context_does_not_leak_result_for_in_progress_match():
    a = md_analysis("1550716", 400)
    ctx = json.dumps(build_context(a, "detailed", "everything"))
    assert "won by" not in ctx


def test_grounding_check_flags_invented_numbers():
    facts = {"score": "110/6", "overs": "25.4", "needed": 132}
    assert grounding_violations("Pakistan are 110/6 after 25.4 overs and need 132.", facts) == []
    assert grounding_violations("They need 150 more and will likely score 187.", facts) == ["150", "187"]
    assert grounding_violations("Two wickets fell in the third over.", facts) == []   # small numbers tolerated


# ---------------------------------------------------------------- Q&A
@pytest.mark.parametrize("q,intent", [
    ("What happened in the last five overs?", "recent"), ("Who scored the most runs?", "top_scorer"),
    ("Which bowler has taken the most wickets?", "top_wickets"), ("How many sixes were hit?", "boundaries"),
    ("What was the biggest partnership?", "partnership"), ("What were the major turning points?", "turning"),
    ("Which player achieved a milestone?", "milestones"), ("Explain the current match situation", "situation"),
    ("Summarize the first innings", "innings_summary"), ("Compare both teams' performances", "compare"),
    ("Why is India under pressure?", "pressure"), ("How did Kohli get out?", "player_out"), ("Who won?", "result"),
])
def test_question_routing(q, intent):
    assert classify(q.lower()) == intent


def test_factual_answers_are_computed_exactly():
    a = small_match()
    top = answer_question(a, "Who scored the most runs?")
    assert "Kohli" in top["answer"] and "30 off 7 balls" in top["answer"]  # 3x4 + 3x6 + 0 = 30 off 7 balls
    assert answer_question(a, "How many sixes were hit?")["answer"].startswith("3 sixes")
    assert "3 fours" in answer_question(a, "how many fours")["answer"]
    w = answer_question(a, "Which bowler has taken the most wickets?")["answer"]
    assert "Starc" in w and "1/" in w


def test_player_dismissal_and_not_out_answers():
    a = small_match()
    out = answer_question(a, "How did Kohli get out?")
    assert "c Smith b Starc" in out["answer"] and out["entities"]["player"] == "Kohli"
    assert "not been dismissed" in answer_question(a, "How did Rohit get out?")["answer"]
    assert "has not faced a ball" in answer_question(a, "How did Head get out?")["answer"]  # at the crease, not out


def test_unavailable_information_is_declined_not_invented():
    r = answer_question(small_match(), "What is the weather like in Mumbai?")
    assert r["intent"] == "unknown" and "can't answer" in r["answer"] and r["suggestions"]
    assert answer_question(small_match(), "")["intent"] == "empty"


def test_result_not_revealed_for_in_progress_match():
    r = answer_question(md_analysis("1550716", 400), "Who won?")
    assert "no result yet" in r["answer"] and "Pakistan won" not in r["answer"]
    done = answer_question(md_analysis("1550716"), "Who won?")
    assert "Pakistan won by 1 wicket" in done["answer"]


def test_find_player_uses_surname_and_prefers_those_who_played():
    a = small_match()
    assert find_player(a, "how many runs did virat kohli make") == "Kohli"
    assert find_player(a, "what about the weather") is None


# ---------------------------------------------------------------- event explanations / insights
def test_event_explanation_uses_measured_facts_only():
    a = small_match()
    ev = next(e for e in a.timeline if e["type"] == "wicket")
    res = explain_event(a, ev["id"])
    assert res["engine"] == "rule-based" and "Kohli" in res["explanation"] and "1st wicket" in res["explanation"]
    assert res["facts"]["partnership_ended"]["runs"] == a.partnerships[0]["runs"]
    assert explain_event(a, "ev-does-not-exist") is None


def test_player_insights_use_actual_statistics_and_state_limitations():
    ins = player_insights(small_match())
    kohli = next(p for p in ins["players"] if p["name"] == "Kohli")
    assert "30 runs from 7 balls" in kohli["insight"] and "3 fours and 3 sixes" in kohli["insight"]
    assert any("contribution score" in x for x in ins["limitations"])


def test_helpers():
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 21)] == ["1st", "2nd", "3rd", "4th", "11th", "12th", "21st"]
    assert plural(1, "six") == "1 six" and plural(2, "six") == "2 sixes" and plural(0, "wicket") == "0 wickets"
