from datetime import datetime

from pydantic import BaseModel

from app.models.attempt import AttemptResult


class RecentAnalytics(BaseModel):
    """Failure statistics for the most recent attempts only."""

    window_size: int
    """How many recent attempts were requested."""
    total_attempts: int
    """How many attempts the window actually covers; fewer than window_size early on."""
    main_bottleneck_phase: int | None = None
    most_common_failure_move: str | None = None
    failure_by_phase: dict[str, int] = {}
    failure_by_move: dict[str, int] = {}


class BossAnalytics(BaseModel):
    # Top-level statistics cover the boss's full attempt history.
    total_attempts: int
    defeated: bool
    best_phase: int | None = None
    main_bottleneck_phase: int | None = None
    most_common_failure_move: str | None = None
    failure_by_phase: dict[str, int] = {}
    failure_by_move: dict[str, int] = {}
    attempts_until_first_victory: int | None = None
    """Attempts up to and including the first victory; None if never defeated."""
    recent: RecentAnalytics


class ProgressionPoint(BaseModel):
    attempt_number: int
    """1 for the boss's first attempt, counting up chronologically."""
    attempt_id: str
    timestamp: datetime
    result: AttemptResult
    phase_reached: int
    failure_move_id: str | None = None
