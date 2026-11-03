"""Cricsheet ingestion pipeline.

    python -m app.data.ingestion                       # import bundled sample matches (works offline)
    python -m app.data.ingestion --dir path/to/jsons   # import a folder of Cricsheet JSON files
    python -m app.data.ingestion --download ipl --limit 25   # download a Cricsheet bundle, import the latest 25 matches
    python -m app.data.ingestion --list-downloads

Steps: validate -> parse -> store matches/teams/players/innings/deliveries/wickets -> compute and persist
partnerships, per-player stats, events, milestones and turning points. Re-running is idempotent.
"""
from __future__ import annotations

import argparse
import json
import logging
import zipfile
from pathlib import Path

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from .. import models as m
from ..config import CACHE_DIR, CRICSHEET_DOWNLOADS, SAMPLES_DIR
from ..database import SessionLocal, init_db
from ..engine.event_detector import build_timeline
from ..engine.match_processor import from_parsed
from ..engine.milestone_detector import detect_milestones
from ..engine.statistics import partnerships, player_stats
from ..engine.turning_points import detect_turning_points
from .cricsheet_parser import ParsedMatch, abbreviate, parse_match
from .data_validator import ValidationError

log = logging.getLogger("matchback.ingest")


class _Ids:
    """Get-or-create caches for teams and players within one ingestion run."""

    def __init__(self, db: Session):
        self.db = db
        self.teams = {t.name: t.id for t in db.scalars(select(m.Team))}
        self.by_cs = {p.cricsheet_id: p.id for p in db.scalars(select(m.Player)) if p.cricsheet_id}
        self.by_name = {p.name: p.id for p in db.scalars(select(m.Player)) if not p.cricsheet_id}

    def team(self, name: str) -> int:
        if name not in self.teams:
            t = m.Team(name=name, abbreviation=abbreviate(name))
            self.db.add(t); self.db.flush()
            self.teams[name] = t.id
        return self.teams[name]

    def player(self, name: str, registry: dict) -> int:
        cs = registry.get(name)
        if cs:
            if cs not in self.by_cs:
                p = m.Player(name=name, cricsheet_id=cs)
                self.db.add(p); self.db.flush()
                self.by_cs[cs] = p.id
            return self.by_cs[cs]
        if name not in self.by_name:
            p = m.Player(name=name)
            self.db.add(p); self.db.flush()
            self.by_name[name] = p.id
        return self.by_name[name]


def import_match(db: Session, pm: ParsedMatch, ids: _Ids, *, force: bool = False) -> bool:
    if db.get(m.Match, pm.match_id):
        if not force:
            return False
        db.execute(delete(m.Match).where(m.Match.id == pm.match_id))
        db.flush()
    md = from_parsed(pm)
    info = pm.info
    meta = md.meta
    row = m.Match(
        id=pm.match_id, data_kind="HISTORICAL", format=pm.format, raw_match_type=info.get("match_type", ""),
        gender=meta["gender"], tournament=meta["tournament"], stage=meta["stage"], season=meta["season"],
        venue=meta["venue"], city=meta["city"], date_start=meta["date_start"], date_end=meta["date_end"],
        team1_id=ids.team(pm.teams[0]), team2_id=ids.team(pm.teams[1]), toss_winner=meta["toss_winner"],
        toss_decision=meta["toss_decision"], winner=(info.get("outcome") or {}).get("winner"),
        outcome=info.get("outcome") or {}, outcome_text=meta["outcome_text"], player_of_match=meta["player_of_match"],
        squads=pm.squads, balls_per_over=md.balls_per_over, overs_limit=md.overs_limit,
        total_deliveries=len(pm.deliveries), data_issues=pm.warnings,
    )
    db.add(row); db.flush()

    totals = {}
    for inn in md.innings:
        g = md.innings_df(inn["innings_no"])
        totals[inn["innings_no"]] = (int(g.total.sum()), int(g.n_wickets.sum()), int(g.legal.sum()))
        db.add(m.Innings(
            match_id=pm.match_id, innings_no=inn["innings_no"], team_id=ids.team(inn["team"]),
            target_runs=inn["target_runs"], target_overs=inn["target_overs"], declared=inn["declared"],
            forfeited=inn["forfeited"], super_over=inn["super_over"], total_runs=totals[inn["innings_no"]][0],
            wickets=totals[inn["innings_no"]][1], legal_balls=totals[inn["innings_no"]][2],
        ))

    pid = lambda name: ids.player(name, pm.registry) if name else None  # noqa: E731
    drows, wrows = [], []
    for d in pm.deliveries:
        drows.append({
            "match_id": pm.match_id, "innings_no": d["innings_no"], "seq": d["seq"], "over_no": d["over_no"],
            "ball_idx": d["ball_idx"], "batter_id": pid(d["batter"]), "non_striker_id": pid(d["non_striker"]),
            "bowler_id": pid(d["bowler"]), "batter_runs": d["batter_runs"], "extras": d["extras"], "total": d["total"],
            "wides": d["wides"], "noballs": d["noballs"], "byes": d["byes"], "legbyes": d["legbyes"],
            "penalty": d["penalty"], "non_boundary": d["non_boundary"], "review": d["review"],
        })
        for w in d["wickets"]:
            wrows.append({"match_id": pm.match_id, "delivery_seq": d["seq"], "innings_no": d["innings_no"], "kind": w["kind"],
                          "player_out_id": pid(w["player_out"] or d["batter"]), "fielders": w["fielders"]})
    db.execute(insert(m.Delivery), drows)
    if wrows:
        db.execute(insert(m.Wicket), wrows)

    # derived artefacts for the complete match
    stats = player_stats(md)
    for s in stats:
        bt, bw, fl = s["batting"] or {}, s["bowling"] or {}, s["fielding"]
        db.add(m.PlayerMatchStatistics(
            match_id=pm.match_id, player_id=pid(s["name"]), team=s["team"] or "", runs=bt.get("runs", 0),
            balls_faced=bt.get("balls", 0), fours=bt.get("fours", 0), sixes=bt.get("sixes", 0),
            wickets=bw.get("wickets", 0), balls_bowled=bw.get("legal_balls", 0), runs_conceded=bw.get("runs", 0),
            maidens=bw.get("maidens", 0), catches=fl["catches"], run_outs=fl["run_outs"], stumpings=fl["stumpings"],
            impact=s["impact"],
        ))
    for p in partnerships(md):
        db.add(m.Partnership(
            match_id=pm.match_id, innings_no=p["innings_no"], wicket_no=p["wicket_no"], batter1=p["batters"][0],
            batter2=p["batters"][1] if len(p["batters"]) > 1 else "", runs=p["runs"], balls=p["balls"],
            start_seq=p["start_seq"], end_seq=p["end_seq"], unbroken=p["unbroken"],
            detail={"contributions": p["contributions"], "ended_by": p["ended_by"]},
        ))
    miles = detect_milestones(md)
    tps = detect_turning_points(md)
    for ms in miles:
        db.add(m.MatchMilestone(match_id=pm.match_id, seq=ms["seq"], innings_no=ms["innings_no"], category=ms["category"],
                                kind=ms["kind"], payload=ms))
    for tp in tps:
        db.add(m.MatchTurningPoint(match_id=pm.match_id, innings_no=tp["innings_no"], start_seq=tp["start_seq"],
                                   end_seq=tp["end_seq"], kind=tp["kind"], score=tp["score"], payload=tp))
    for ev in build_timeline(md, miles, tps):
        db.add(m.MatchEvent(match_id=pm.match_id, seq=ev["seq"], innings_no=ev["innings_no"], type=ev["type"], payload=ev))
    return True


def ingest_files(paths: list[Path], *, force: bool = False) -> dict:
    init_db()
    report = {"imported": 0, "skipped_existing": 0, "failed": []}
    with SessionLocal() as db:
        ids = _Ids(db)
        for p in paths:
            try:
                raw = json.loads(Path(p).read_text(encoding="utf8"))
                pm = parse_match(raw, Path(p).stem)
                with db.begin_nested():
                    if import_match(db, pm, ids, force=force):
                        report["imported"] += 1
                        log.info("imported %s: %s", pm.match_id, " vs ".join(pm.teams))
                    else:
                        report["skipped_existing"] += 1
            except (ValidationError, KeyError, ValueError, json.JSONDecodeError) as exc:
                report["failed"].append({"file": str(p), "error": str(exc)})
                log.warning("skipped %s: %s", p, exc)
        db.commit()
    return report


def download_bundle(name: str) -> Path:
    """Download a Cricsheet JSON zip into the cache and extract only `*.json` files (flat, by basename)."""
    if name not in CRICSHEET_DOWNLOADS:
        raise SystemExit(f"Unknown bundle '{name}'. Options: {', '.join(CRICSHEET_DOWNLOADS)}")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    zpath = CACHE_DIR / f"{name}.zip"
    out = CACHE_DIR / name
    out.mkdir(exist_ok=True)
    log.info("downloading %s ...", CRICSHEET_DOWNLOADS[name])
    with httpx.stream("GET", CRICSHEET_DOWNLOADS[name], follow_redirects=True, timeout=120) as r:
        r.raise_for_status()
        with zpath.open("wb") as fh:
            for chunk in r.iter_bytes():
                fh.write(chunk)
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            base = Path(info.filename).name
            if base.endswith(".json"):
                (out / base).write_bytes(z.read(info))
    return out


def latest_files(folder: Path, limit: int) -> list[Path]:
    dated = []
    for f in folder.glob("*.json"):
        try:
            dated.append((json.loads(f.read_text(encoding="utf8"))["info"]["dates"][-1], f))
        except (KeyError, ValueError, json.JSONDecodeError):
            continue
    dated.sort(reverse=True)
    return [f for _, f in dated[:limit]]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path, help="folder of Cricsheet JSON files")
    ap.add_argument("--files", nargs="*", type=Path, help="specific JSON files")
    ap.add_argument("--download", help="Cricsheet bundle name (see --list-downloads)")
    ap.add_argument("--limit", type=int, default=25, help="with --download/--dir: import the N most recent matches")
    ap.add_argument("--force", action="store_true", help="re-import matches that already exist")
    ap.add_argument("--list-downloads", action="store_true")
    a = ap.parse_args()
    if a.list_downloads:
        for k, v in CRICSHEET_DOWNLOADS.items():
            print(f"{k:14s} {v}")
        return
    if a.download:
        files = latest_files(download_bundle(a.download), a.limit)
    elif a.dir:
        files = latest_files(a.dir, a.limit)
    elif a.files:
        files = a.files
    else:
        files = sorted(SAMPLES_DIR.glob("*.json"))
    rep = ingest_files(files, force=a.force)
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
