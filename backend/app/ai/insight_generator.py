"""Per-player written insights. Deterministic templates over verified statistics - no model needed, so
no risk of invented figures and instant for every player card."""
from __future__ import annotations

from ..analysis import Analysis
from .fallback_generator import batting_insight, bowling_insight, plural

LIMITATIONS = [
    "Figures cover this match only; averages need several dismissals to mean much.",
    "Strike rate and economy highlights use minimum ball thresholds so short cameos do not dominate.",
    "The contribution score is a simple custom weighted sum (runs, boundaries, wickets, maidens, catches...). "
    "It ignores pitch, opposition, match situation and pressure, so treat it as a rough guide, not a verdict.",
    "Roles are inferred from what the player did in this match; Cricsheet does not record official roles.",
]


def player_insights(a: Analysis) -> dict:
    cards = []
    for s in a.player_stats:
        parts = [t for t in (batting_insight(s), bowling_insight(s)) if t]
        f = s["fielding"]
        if f["catches"] or f["stumpings"] or f["run_outs"]:
            bits = [x for x in (plural(f["catches"], "catch") if f["catches"] else "", plural(f["stumpings"], "stumping") if f["stumpings"] else "",
                                plural(f["run_outs"], "run-out") if f["run_outs"] else "") if x]
            parts.append(f"In the field: {', '.join(bits)}.")
        if not parts:
            continue
        cards.append({**s, "insight": " ".join(parts), "indicator": _indicator(s)})
    return {"players": cards, "highlights": a.highlights, "limitations": LIMITATIONS, "engine": "rule-based (verified statistics)"}


def _indicator(s: dict) -> str:
    imp = s["impact"]
    return "outstanding" if imp >= 90 else "strong" if imp >= 45 else "steady" if imp >= 15 else "limited"
