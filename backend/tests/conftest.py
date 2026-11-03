"""Helpers that build small Cricsheet-shaped matches whose correct answers can be worked out by hand."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.analysis import Analysis  # noqa: E402
from app.data.cricsheet_parser import parse_match  # noqa: E402
from app.engine.match_processor import from_parsed  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"


def ball(batter="A", non="B", bowler="X", runs=0, extras=None, wicket=None, boundary_run=False):
    extras = extras or {}
    ex = sum(extras.values())
    d = {"batter": batter, "bowler": bowler, "non_striker": non, "runs": {"batter": runs, "extras": ex, "total": runs + ex}}
    if boundary_run:
        d["runs"]["non_boundary"] = True
    if extras:
        d["extras"] = extras
    if wicket:
        d["wickets"] = [wicket]
    return d


def wk(kind, out="A", fielders=None):
    w = {"kind": kind, "player_out": out}
    if fielders:
        w["fielders"] = [{"name": f} for f in fielders]
    return w


def overs_of(balls, per_over=6):
    """Split a flat list of deliveries into Cricsheet overs (illegal balls stay inside their over)."""
    out, cur, legal, n = [], [], 0, 0
    for b in balls:
        cur.append(b)
        if not (b.get("extras", {}).get("wides") or b.get("extras", {}).get("noballs")):
            legal += 1
        if legal == per_over:
            out.append({"over": n, "deliveries": cur}); cur, legal, n = [], 0, n + 1
    if cur:
        out.append({"over": n, "deliveries": cur})
    return out


def raw_match(innings, match_type="T20", teams=("Alpha", "Beta"), overs=20, target=None, **info_extra):
    info = {"balls_per_over": 6, "dates": ["2026-01-01"], "gender": "male", "match_type": match_type, "teams": list(teams),
            "venue": "Test Ground", "toss": {"winner": teams[0], "decision": "bat"},
            "outcome": {"winner": teams[0], "by": {"runs": 10}}, **info_extra}
    if overs is not None:
        info["overs"] = overs
    return {"meta": {"data_version": "1.2.0"}, "info": info,
            "innings": [{"team": teams[i % 2], "overs": overs_of(b) if isinstance(b, list) else b,
                         **({"target": {"runs": target, "overs": overs}} if i == 1 and target else {})}
                        for i, b in enumerate(innings)]}


def make_md(innings, match_type="T20", **kw):
    return from_parsed(parse_match(raw_match(innings, match_type, **kw), "t1"))


def make_analysis(innings, match_type="T20", cutoff=None, **kw):
    return Analysis(make_md(innings, match_type, **kw), cutoff)


@pytest.fixture(scope="session")
def sample_files():
    return {p.stem: p for p in SAMPLES.glob("*.json")}


def md_from_sample(name):
    from app.data.cricsheet_parser import load_match_file
    return from_parsed(load_match_file(SAMPLES / f"{name}.json"))
