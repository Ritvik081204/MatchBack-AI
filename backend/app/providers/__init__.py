from .base import MatchDataProvider
from .demo import DemoMatchProvider
from .historical import HistoricalMatchProvider
from .live import OptionalLiveMatchProvider

historical = HistoricalMatchProvider()
demo = DemoMatchProvider()
live = OptionalLiveMatchProvider()

PROVIDERS: list[MatchDataProvider] = [live, demo, historical]  # order matters: most specific id prefix first


def provider_for(match_id: str) -> MatchDataProvider:
    return next(p for p in PROVIDERS if p.owns(match_id))


def provider_status() -> list[dict]:
    return [
        {"name": "live", "data_kind": "LIVE", "available": live.configured,
         "note": "No free, documented live-score API is configured. See providers/live.py to plug one in."},
        {"name": "demo", "data_kind": "DEMO", "available": True,
         "note": "Real historical matches replayed from a chosen point. Not live."},
        {"name": "historical", "data_kind": "HISTORICAL", "available": True,
         "note": "Completed matches imported from Cricsheet ball-by-ball data."},
    ]


__all__ = ["MatchDataProvider", "provider_for", "provider_status", "historical", "demo", "live"]
