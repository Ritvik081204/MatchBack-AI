"""Lazy, cached bundle of every derived artefact for one (match, cut-off) pair.

Routers, the AI context builder and the Q&A engine all read from this, so each statistic is computed once
and the numbers shown in the UI, the recap and the chat answers can never disagree."""
from __future__ import annotations

from collections import OrderedDict
from functools import cached_property

from .engine import event_detector, milestone_detector, statistics, turning_points
from .engine.match_processor import MatchData, situation

_CACHE: "OrderedDict[tuple, Analysis]" = OrderedDict()
_MAX = 48


class Analysis:
    def __init__(self, full: MatchData, cutoff: int | None):
        self.md: MatchData = full.upto(cutoff)

    @cached_property
    def situation(self) -> dict:
        return situation(self.md)

    @cached_property
    def scorecard(self) -> list[dict]:
        return statistics.scorecard(self.md)

    @cached_property
    def player_stats(self) -> list[dict]:
        return statistics.player_stats(self.md)

    @cached_property
    def highlights(self) -> dict:
        return statistics.highlights(self.md, self.player_stats)

    @cached_property
    def overs(self) -> list[dict]:
        return statistics.over_by_over(self.md)

    @cached_property
    def partnerships(self) -> list[dict]:
        return statistics.partnerships(self.md)

    @cached_property
    def phases(self) -> dict[int, list[dict]]:
        return {i["innings_no"]: statistics.phases(self.md, i["innings_no"]) for i in self.md.innings}

    @cached_property
    def milestones(self) -> list[dict]:
        return milestone_detector.detect_milestones(self.md)

    @cached_property
    def turning_points(self) -> list[dict]:
        return turning_points.detect_turning_points(self.md)

    @cached_property
    def timeline(self) -> list[dict]:
        return event_detector.build_timeline(self.md, self.milestones, self.turning_points)

    @cached_property
    def momentum(self) -> list[dict]:
        return turning_points.momentum_series(self.md)

    def event(self, event_id: str) -> dict | None:
        return next((e for e in self.timeline if e["id"] == event_id), None)


def get_analysis(full: MatchData, cutoff: int | None) -> Analysis:
    key = (full.match_id, cutoff if cutoff is not None and cutoff < full.max_seq else None)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]
    a = Analysis(full, key[1])
    _CACHE[key] = a
    if len(_CACHE) > _MAX:
        _CACHE.popitem(last=False)
    return a
