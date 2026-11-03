"""Provider-independent data access. The event-processing and AI layers only ever see `MatchData`
(see engine.match_processor), so adding a new source (e.g. a licensed live-score feed) means implementing
this interface and registering it in providers/__init__.py - nothing else changes."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..engine.match_processor import MatchData


class MatchDataProvider(ABC):
    name: str = "base"
    data_kind: str = "HISTORICAL"  # LIVE | HISTORICAL | DEMO - always surfaced in the UI

    @abstractmethod
    def get_matches(self, *, q: str | None = None, fmt: str | None = None, gender: str | None = None,
                    limit: int = 20, offset: int = 0) -> tuple[int, list[dict]]:
        """Return (total, page of match summaries)."""

    @abstractmethod
    def get_match_details(self, match_id: str, cutoff: int | None = None) -> dict | None: ...

    @abstractmethod
    def get_live_matches(self) -> list[dict]: ...

    @abstractmethod
    def get_scorecard(self, match_id: str, cutoff: int | None = None) -> list[dict] | None: ...

    @abstractmethod
    def get_ball_by_ball(self, match_id: str, cutoff: int | None = None) -> list[dict] | None: ...

    @abstractmethod
    def get_player_statistics(self, player_id: str) -> dict | None: ...

    @abstractmethod
    def get_match_data(self, match_id: str, cutoff: int | None = None) -> MatchData | None:
        """Hook used by the analytics/AI layers. Must return data truncated to `cutoff` when given."""

    def owns(self, match_id: str) -> bool:
        return False
