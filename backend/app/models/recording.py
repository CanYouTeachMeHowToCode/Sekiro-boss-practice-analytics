from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class RecordingStatus(str, Enum):
    UPLOADED = "uploaded"
    CHECKING = "checking"
    REJECTED = "rejected"
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class FailureType(str, Enum):
    DAMAGE = "damage"
    POSTURE_BREAK = "posture_break"
    DEATH = "death"


class Recording(BaseModel):
    id: str
    # the boss fought in the recording (castle Genichiro in M3), whose moveset names the report's moves
    boss_id: str
    filename: str
    status: RecordingStatus
    # why it was rejected, as a code the frontend translates
    reject_code: str | None = None
    progress: float
    size_bytes: int
    duration_s: float | None = None
    # the video's size, known once the worker has checked it
    width: int | None = None
    height: int | None = None
    # below the recommended 1080p: analysed, but fewer failures get a sure move, which the report tells the user
    low_resolution: bool = False
    created_at: datetime
    processed_at: datetime | None = None


class MoveCandidate(BaseModel):
    move_id: str
    score: float


class FailureEvent(BaseModel):
    type: FailureType
    time_s: float


class RecordingFailure(BaseModel):
    id: str
    time_s: float
    type: FailureType
    phase: int
    # the move is given only when the system is sure of it; otherwise the candidates say what it might be
    sure: bool
    move_id: str | None = None
    candidates: list[MoveCandidate] = []
    events: list[FailureEvent] = []
    has_clip: bool


class MoveFailureCount(BaseModel):
    """Failures per move, from the failures whose move the system is sure of. These are failure counts, not success
    rates: how often each move occurred is not known."""

    move_id: str
    damage: int
    posture_break: int
    death: int
    total: int


class RecordingReport(BaseModel):
    recording: Recording
    failures: list[RecordingFailure]
    by_move: list[MoveFailureCount]
    # failures whose move the system is not sure of
    uncertain: int


class AdminRecording(Recording):
    """A recording in the read-only admin view (owner decision, 2026-11-18): whose it is, and the worker's error."""

    owner: str
    error: str | None = None
    fps: float | None = None


class AdminRecordingReport(RecordingReport):
    owner: str
