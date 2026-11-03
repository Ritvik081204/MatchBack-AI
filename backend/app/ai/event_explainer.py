from __future__ import annotations

import json

from ..analysis import Analysis
from ..engine.event_detector import event_facts
from . import prompt_templates as pt
from .fallback_generator import fallback_event_explanation
from .llm_service import grounding_violations, llm


def explain_event(a: Analysis, event_id: str, use_llm: bool = True) -> dict | None:
    ev = a.event(event_id)
    if not ev:
        return None
    facts = event_facts(a.md, ev, a.milestones, a.turning_points)
    text, engine = None, "rule-based"
    if use_llm and llm.available:
        facts_json = json.dumps(facts, default=str)
        out = llm.generate(pt.EXPLAIN_SYSTEM, pt.explain_prompt(ev["title"], facts_json), 140)
        if out and len(grounding_violations(out, facts_json)) <= 1:
            text, engine = out, f"ollama:{llm.model}"
    if not text:
        text = fallback_event_explanation(facts, ev["title"])
    return {"event_id": event_id, "title": ev["title"], "explanation": text, "engine": engine, "facts": facts,
            "basis": "Derived only from this match's recorded deliveries up to the current position."}
