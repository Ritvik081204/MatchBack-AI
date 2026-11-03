"""Validation of raw Cricsheet JSON before processing.

Fatal problems raise ValidationError (the match is skipped); non-fatal ones are
returned as warnings and stored with the match so the UI can disclose them.
"""
from __future__ import annotations


class ValidationError(ValueError):
    pass


def validate_raw(raw: dict) -> list[str]:
    """Return a list of non-fatal warnings; raise ValidationError for unusable input."""
    if not isinstance(raw, dict):
        raise ValidationError("match file is not a JSON object")
    info = raw.get("info")
    if not isinstance(info, dict):
        raise ValidationError("missing 'info' block")
    teams = info.get("teams")
    if not isinstance(teams, list) or len(teams) != 2:
        raise ValidationError("'info.teams' must list exactly two teams")
    if not info.get("dates"):
        raise ValidationError("missing match dates")
    innings = raw.get("innings")
    if not isinstance(innings, list) or not innings:
        raise ValidationError("no innings recorded")

    warnings: list[str] = []
    if not info.get("match_type"):
        warnings.append("match_type missing; format inferred from overs limit")
    if not info.get("venue"):
        warnings.append("venue missing")
    if not info.get("players"):
        warnings.append("squad lists missing; role/yet-to-bat info unavailable")
    if not (info.get("registry") or {}).get("people"):
        warnings.append("player registry missing; players are identified by name only")
    for i, inn in enumerate(innings, start=1):
        if not isinstance(inn, dict) or "overs" not in inn or "team" not in inn:
            raise ValidationError(f"innings {i} is malformed (needs 'team' and 'overs'; legacy format unsupported)")
        if not inn["overs"]:
            warnings.append(f"innings {i} has no deliveries")
    return warnings


def validate_delivery(d: dict, where: str) -> None:
    for key in ("batter", "bowler", "runs"):
        if key not in d:
            raise ValidationError(f"{where}: delivery missing '{key}'")
    runs = d["runs"]
    if not isinstance(runs, dict) or "total" not in runs:
        raise ValidationError(f"{where}: delivery 'runs' malformed")
