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
    filename: str
    status: RecordingStatus
    # why it was rejected, as a code the frontend translates
    reject_code: str | None = None
    progress: float
    size_bytes: int
    duration_s: float | None = None
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
