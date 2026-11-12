"""What the worker needs from the failure attribution pipeline.

An analyzer takes a video and returns the failures in it, each with its move when the pipeline is sure of it and its
candidates otherwise. Version 2 of the pipeline (research/failure_attribution) will be packaged as one once it is
frozen and has passed its test; until then there is none, and queued recordings wait.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class FoundFailure:
    time_s: float
    type: str                                   # damage, posture_break or death
    phase: int
    sure: bool
    move: str | None = None                     # the move's slug, given only when sure
    candidates: tuple[tuple[str, float], ...] = ()   # (slug, score), best first
    events: tuple[tuple[str, float], ...] = ()       # (type, time_s) of the events merged into this failure


class Analyzer(Protocol):
    version: str

    def analyze(self, video: Path, progress: Callable[[float], None]) -> list[FoundFailure]:
        """The failures in the video; calls progress with a fraction from 0 to 1 as it goes."""
        ...


def load_analyzer() -> Analyzer | None:
    """The installed pipeline version, or None while none is."""
    return None
