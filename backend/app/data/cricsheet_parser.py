"""Parse a Cricsheet JSON match (data_version 1.x with `innings[].overs[].deliveries[]`) into flat, typed records.

Cricsheet specifics handled here:
* extras are a dict of kinds: wides / noballs / byes / legbyes / penalty
* a delivery is *legal* unless it carries wides or noballs
* `runs.non_boundary` marks four/six-valued runs that were run, not hit
* wickets are a list (a delivery may carry more than one)
* Test innings may be `declared` / `forfeited`; limited-overs chases carry a `target`
* super-over innings are flagged `super_over`
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .data_validator import ValidationError, validate_delivery, validate_raw

FORMAT_MAP = {"T20": "T20", "IT20": "T20", "ODI": "ODI", "ODM": "ODI", "Test": "TEST", "MDM": "TEST"}
NON_TEAM_WICKETS = {"retired hurt", "retired not out"}  # batter leaves, no wicket falls


@dataclass
class ParsedInnings:
    innings_no: int
    team: str
    target_runs: int | None = None
    target_overs: float | None = None
    declared: bool = False
    forfeited: bool = False
    super_over: bool = False


@dataclass
class ParsedMatch:
    match_id: str
    info: dict
    format: str
    teams: list[str]
    squads: dict[str, list[str]]
    registry: dict[str, str]
    innings: list[ParsedInnings] = field(default_factory=list)
    deliveries: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def infer_format(info: dict) -> str:
    mt = info.get("match_type")
    if mt in FORMAT_MAP:
        return FORMAT_MAP[mt]
    overs = info.get("overs")
    if overs is None:
        return "TEST"
    return "T20" if overs <= 20 else "ODI"


def outcome_text(info: dict) -> str:
    o = info.get("outcome") or {}
    if not o:
        return "Result not recorded"
    by = o.get("by") or {}
    winner = o.get("winner")
    if winner:
        if "innings" in by:
            txt = f"{winner} won by an innings and {by.get('runs', 0)} runs"
        elif "runs" in by:
            txt = f"{winner} won by {by['runs']} run{'s' if by['runs'] != 1 else ''}"
        elif "wickets" in by:
            txt = f"{winner} won by {by['wickets']} wicket{'s' if by['wickets'] != 1 else ''}"
        else:
            txt = f"{winner} won"
        if o.get("method"):
            txt += f" ({o['method']})"
        if o.get("eliminator"):
            txt = f"Tied - {o['eliminator']} won the super over"
        if o.get("bowl_out"):
            txt = f"Tied - {o['bowl_out']} won the bowl-out"
        return txt
    result = o.get("result", "no result")
    return {"tie": "Match tied", "draw": "Match drawn", "no result": "No result"}.get(result, result.capitalize())


def abbreviate(name: str) -> str:
    """Generated team abbreviation (no flags/logos used - avoids third-party assets)."""
    words = [w for w in name.replace("-", " ").split() if w.lower() not in {"of", "the", "and"}]
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words)[:4].upper()


def parse_match(raw: dict, match_id: str) -> ParsedMatch:
    warnings = validate_raw(raw)
    info = raw["info"]
    fmt = infer_format(info)
    pm = ParsedMatch(
        match_id=str(match_id),
        info=info,
        format=fmt,
        teams=list(info["teams"]),
        squads=info.get("players") or {},
        registry=(info.get("registry") or {}).get("people") or {},
        warnings=warnings,
    )
    seq = 0
    for inn_no, inn in enumerate(raw["innings"], start=1):
        target = inn.get("target") or {}
        pm.innings.append(ParsedInnings(
            innings_no=inn_no, team=inn["team"],
            target_runs=target.get("runs"), target_overs=target.get("overs"),
            declared=bool(inn.get("declared")), forfeited=bool(inn.get("forfeited")),
            super_over=bool(inn.get("super_over")),
        ))
        for ov in inn["overs"]:
            over_no = int(ov["over"])
            ball_idx = 0
            for d in ov.get("deliveries", []):
                ball_idx += 1
                validate_delivery(d, f"innings {inn_no} over {over_no}")
                runs = d["runs"]
                ex = d.get("extras") or {}
                wickets = [
                    {
                        "kind": w.get("kind", "unknown"),
                        "player_out": w.get("player_out"),
                        "fielders": [f.get("name") for f in (w.get("fielders") or []) if f.get("name")],
                    }
                    for w in (d.get("wickets") or [])
                ]
                pm.deliveries.append({
                    "seq": seq,
                    "innings_no": inn_no,
                    "over_no": over_no,
                    "ball_idx": ball_idx,
                    "batter": d["batter"],
                    "non_striker": d.get("non_striker"),
                    "bowler": d["bowler"],
                    "batter_runs": int(runs.get("batter", 0)),
                    "extras": int(runs.get("extras", 0)),
                    "total": int(runs["total"]),
                    "wides": int(ex.get("wides", 0)),
                    "noballs": int(ex.get("noballs", 0)),
                    "byes": int(ex.get("byes", 0)),
                    "legbyes": int(ex.get("legbyes", 0)),
                    "penalty": int(ex.get("penalty", 0)),
                    "non_boundary": bool(runs.get("non_boundary", False)),
                    "wickets": wickets,
                    "review": d.get("review"),
                })
                seq += 1
    if not pm.deliveries:
        raise ValidationError("match contains no deliveries")
    return pm


def load_match_file(path: str | Path) -> ParsedMatch:
    path = Path(path)
    with path.open(encoding="utf8") as fh:
        raw = json.load(fh)
    return parse_match(raw, path.stem)
