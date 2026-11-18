"""What the worker needs from the failure attribution pipeline, and the installed pipeline.

An analyzer checks that a video is a castle Genichiro fight (check) and finds the failures in it (analyze), each with
its move when the pipeline is sure of it and its candidates otherwise. The pipeline is the analysis package
(analysis/sekiro_analysis, version 2), installed in the worker's image; it needs a local data folder
(ANALYSIS_DATA_DIR) with the references taken from the owner's recordings and the game's images, which are never in
the repository (research/failure_attribution/scripts/export_analysis_data.py writes it). Without the package or the
folder, or when the image decodes video differently from the research, there is no analyzer, and queued recordings
wait.
"""

import logging
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

log = logging.getLogger(__name__)


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

    def check(self, video: Path) -> str | None:
        """Why the video is not a castle Genichiro fight, as a reject code, or None when it is."""
        ...

    def analyze(self, video: Path, progress: Callable[[float], None]) -> list[FoundFailure]:
        """The failures in the video; calls progress with a fraction from 0 to 1 as it goes."""
        ...


class PipelineAnalyzer:
    """The analysis package. Each analysis runs in a temporary work folder, removed afterwards."""

    def __init__(self, data_dir: str, device: str | None = None):
        from sekiro_analysis import pipeline

        self._pipeline = pipeline
        self.data = pipeline.Data(data_dir)
        self.device = device or pipeline.default_device()
        self.version = pipeline.VERSION

    def check(self, video: Path) -> str | None:
        code, scores = self._pipeline.check(video, self.data, self.device)
        log.info("upload check of %s: %s %s", video.name, code or "castle Genichiro", scores)
        return code

    def analyze(self, video: Path, progress: Callable[[float], None]) -> list[FoundFailure]:
        with tempfile.TemporaryDirectory(prefix="analysis-") as work:
            found = self._pipeline.analyze(video, work, self.data, self.device, progress)
        return [FoundFailure(time_s=f.time_s, type=f.type, phase=f.phase, sure=f.sure, move=f.move,
                             candidates=f.candidates, events=f.events) for f in found]


def load_analyzer() -> Analyzer | None:
    """The installed pipeline, or None (and why, in the log) while the package or its data folder is missing or the
    decoding is not the research's."""
    folder = os.environ.get("ANALYSIS_DATA_DIR")
    if not folder:
        log.warning("ANALYSIS_DATA_DIR is not set: no pipeline")
        return None
    try:
        from sekiro_analysis.pipeline import Data
    except ImportError as exc:
        log.warning("the analysis package is not installed (%s): no pipeline", exc)
        return None
    missing = Data(folder).missing()
    if missing:
        log.warning("the analysis data folder %s lacks %s: no pipeline", folder, ", ".join(missing))
        return None
    # The steps read the HUD and the boss from decoded pixels; with another decoding the results would differ from
    # the measured version 2 (sekiro_analysis/decode.py).
    from sekiro_analysis import decode

    if not decode.same_as_research():
        log.error("this image's OpenCV decodes video differently from the research (sekiro_analysis/decode.py): "
                  "no pipeline")
        return None
    return PipelineAnalyzer(folder, os.environ.get("ANALYSIS_DEVICE") or None)
