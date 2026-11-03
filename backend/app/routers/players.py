from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from .. import models as m
from ..database import SessionLocal
from ..providers import historical
from ..utils import clean

router = APIRouter(prefix="/api/players", tags=["players"])


@router.get("/{player_id}")
def player(player_id: str):
    with SessionLocal() as db:
        try:
            p = db.get(m.Player, int(player_id))
        except ValueError:
            p = None
        if not p:
            raise HTTPException(404, "Player not found")
        return {"id": p.id, "name": p.name, "cricsheet_id": p.cricsheet_id,
                "note": "Only the name and per-match statistics from ingested matches are available; no biography or career data."}


@router.get("/{player_id}/statistics")
def statistics(player_id: str):
    res = historical.get_player_statistics(player_id)
    if res is None:
        raise HTTPException(404, "Player not found")
    return clean(res)
