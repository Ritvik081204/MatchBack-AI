"""Optional live provider - intentionally inert.

No free, officially documented live-score API with ball-by-ball data and permissive terms was identified for
this project, and undocumented endpoints are not used. To add one:

1. subclass `MatchDataProvider`, return `MatchData` built with `engine.match_processor.build_match_data`
   from the provider's ball-by-ball feed (same dict shape as `data.cricsheet_parser`),
2. set `data_kind = "LIVE"`,
3. register it in `providers/__init__.py`.

The analytics, timeline, AI recap and Q&A layers need no changes.
"""
from __future__ import annotations

from ..engine.match_processor import MatchData
from .base import MatchDataProvider


class OptionalLiveMatchProvider(MatchDataProvider):
    name = "live"
    data_kind = "LIVE"
    configured = False

    def owns(self, match_id: str) -> bool:
        return match_id.startswith("live-")

    def get_matches(self, *, q=None, fmt=None, gender=None, limit=20, offset=0):  # noqa: ANN001
        return 0, []

    def get_match_details(self, match_id: str, cutoff: int | None = None) -> dict | None:
        return None

    def get_live_matches(self) -> list[dict]:
        return []

    def get_scorecard(self, match_id: str, cutoff: int | None = None):
        return None

    def get_ball_by_ball(self, match_id: str, cutoff: int | None = None):
        return None

    def get_player_statistics(self, player_id: str):
        return None

    def get_match_data(self, match_id: str, cutoff: int | None = None) -> MatchData | None:
        return None
