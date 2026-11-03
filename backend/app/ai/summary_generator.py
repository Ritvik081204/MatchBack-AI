"""AI catch-up recap: Python computes facts -> compact context -> LLM narrates (or rule-based fallback)."""
from __future__ import annotations

import json
import time

from ..analysis import Analysis
from . import prompt_templates as pt
from .context_builder import build_context
from .fallback_generator import WORD_TARGET, fallback_recap
from .llm_service import grounding_violations, llm

LENGTHS = ("quick", "standard", "detailed")
FOCUSES = ("everything", "players", "wickets", "milestones", "situation")
MAX_TOKENS = {"quick": 220, "standard": 420, "detailed": 800}


def _trim_to_sentence(text: str) -> str:
    """If the model hit its token cap mid-sentence, drop the dangling fragment."""
    text = text.strip()
    if text and text[-1] in ".!?\"')":
        return text
    cut = max(text.rfind(". "), text.rfind("! "), text.rfind("? "))
    return text[: cut + 1] if cut > 40 else text


def generate_recap(a: Analysis, length: str = "quick", focus: str = "everything", use_llm: bool = True) -> dict:
    length = length if length in LENGTHS else "quick"
    focus = focus if focus in FOCUSES else "everything"
    t0 = time.perf_counter()
    ctx = build_context(a, length, focus)
    ctx_json = json.dumps(ctx, separators=(",", ":"), default=str)

    engine, note, paragraphs = "rule-based", None, None
    if use_llm and llm.available:
        text = llm.generate(pt.RECAP_SYSTEM, pt.recap_prompt(ctx_json, length, focus), MAX_TOKENS[length])
        if text:
            text = _trim_to_sentence(text)
            bad = grounding_violations(text, ctx_json)
            if len(bad) <= 1:
                engine = f"ollama:{llm.model}"
                paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            else:
                note = f"LLM output contained figures not in the match data ({', '.join(bad[:4])}); showing the rule-based recap instead."
        else:
            note = "LLM did not respond in time; showing the rule-based recap."
    elif use_llm:
        note = "Local LLM (Ollama) not available; showing the rule-based recap built from the same verified facts."
    if paragraphs is None:
        paragraphs = fallback_recap(ctx)

    sit = a.situation
    return {
        "length": length, "focus": focus, "engine": engine, "note": note, "paragraphs": paragraphs,
        "word_count": sum(len(p.split()) for p in paragraphs), "target_words": WORD_TARGET[length],
        "read_seconds": round(sum(len(p.split()) for p in paragraphs) / 3.3),
        "as_of": {"innings": sit["innings_no"], "score": sit["score"], "overs": sit["overs"]},
        "generated_ms": round((time.perf_counter() - t0) * 1000),
        "context_chars": len(ctx_json),
        "key_facts": {"score": sit["score"], "overs": sit["overs"], "status": sit["status"]},
    }
