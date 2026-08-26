from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class AttemptResult(str, Enum):
    FAILED = "failed"
    VICTORY = "victory"


class FailureCategory(str, Enum):
    NOT_SURE = "not_sure"
    OTHER = "other"


class CreateAttemptRequest(BaseModel):
    result: AttemptResult
    phase_reached: int | None = None
    failure_move_id: str | None = None
    failure_category: FailureCategory | None = None
    notes: str = ""


class Attempt(BaseModel):
    id: str
    boss_id: str
    timestamp: datetime
    result: AttemptResult
    phase_reached: int
    failure_move_id: str | None = None
    failure_category: FailureCategory | None = None
    notes: str = ""
