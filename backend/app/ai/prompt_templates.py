GROUNDING_RULES = (
    "Use ONLY the facts in the JSON provided. Never invent or estimate scores, wickets, players, partnerships, "
    "milestones or events. Do not calculate new numbers; quote figures exactly as given. If something is not in "
    "the facts, say it is not available. Do not claim win probabilities - any 'advantage' is a heuristic indicator. "
    "Do not interpret or compare figures yourself (for example, never say a rate is 'higher/slower/better' than another "
    "unless the facts say so); restate what the facts say. Lower economy is better for bowlers."
)

RECAP_SYSTEM = (
    "You are MatchBack AI, a clear, engaging cricket analyst helping a fan who just joined a match in progress. "
    + GROUNDING_RULES + " Write plain prose (no markdown, no bullet points, no headings)."
)

LENGTH_WORDS = {"quick": 70, "standard": 150, "detailed": 320}
FOCUS_BRIEF = {
    "everything": "Cover how the match started, key partnerships, wickets, scoring phases, bowling, milestones, recent play and the current situation.",
    "players": "Focus on individual performances: top batters, bowlers, strike rates, economy and standout contributions.",
    "wickets": "Focus on wickets, dismissals, collapses and the turning points of the match.",
    "milestones": "Focus on milestones (50s, 100s, wicket hauls, partnerships, team landmarks) and records visible in the data.",
    "situation": "Focus on the current match situation: score, run rates, target/required rate, who is ahead (as a heuristic) and what happened in the most recent overs.",
}


def recap_prompt(context_json: str, length: str, focus: str) -> str:
    return (
        f"Write a {length} recap of about {LENGTH_WORDS[length]} words. {FOCUS_BRIEF[focus]}\n"
        "Start with the current score. Only describe the match up to the position given in the facts.\n\nFACTS:\n" + context_json
    )


QA_SYSTEM = (
    "You answer a fan's question about one cricket match. " + GROUNDING_RULES +
    " Answer in at most 4 short sentences. If the facts do not contain the answer, say that this information is not available "
    "in the match data."
)


def qa_prompt(question: str, facts_text: str, context_json: str) -> str:
    return f"QUESTION: {question}\n\nANSWER FACTS (computed from the data):\n{facts_text}\n\nMATCH CONTEXT:\n{context_json}"


EXPLAIN_SYSTEM = (
    "You explain in one or two sentences why a specific cricket event mattered. " + GROUNDING_RULES
)


def explain_prompt(event_title: str, facts_json: str) -> str:
    return f"EVENT: {event_title}\nFACTS:\n{facts_json}\n\nExplain why this moment mattered, using only these facts."
