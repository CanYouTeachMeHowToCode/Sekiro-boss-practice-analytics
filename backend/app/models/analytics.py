from datetime import datetime

from pydantic import BaseModel

from app.models.attempt import AttemptResult, FailureCategory


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


class BossComparisonRow(BaseModel):
    id: str
    name: str
    name_zh: str | None = None
    total_phases: int
    attempts: int
    best_phase: int | None = None
    defeated: bool
    attempts_until_first_victory: int | None = None
    last_attempt_at: datetime | None = None


class RecentAttempt(BaseModel):
    attempt_id: str
    boss_id: str
    boss_name: str
    timestamp: datetime
    result: AttemptResult
    phase_reached: int
    failure_move_id: str | None = None
    failure_move_name: str | None = None
    failure_move_name_zh: str | None = None
    boss_name_zh: str | None = None
    failure_category: FailureCategory | None = None


class SekiroAnalytics(BaseModel):
    total_bosses: int
    bosses_attempted: int
    bosses_defeated: int
    total_attempts: int
    most_practiced_bosses: list[str]
    """Boss ids with the most attempts; more than one when tied."""
    most_attempts_to_defeat: int | None = None
    """The highest attempts_until_first_victory among defeated bosses."""
    bosses_requiring_most_attempts: list[str]
    """Defeated boss ids whose first victory took most_attempts_to_defeat attempts."""
    recent_window_days: int
    attempts_in_recent_window: int
    recent_attempts: list[RecentAttempt]
    """Newest first, across all bosses."""
    bosses: list[BossComparisonRow]


class ProgressionPoint(BaseModel):
    attempt_number: int
    """1 for the boss's first attempt, counting up chronologically."""
    attempt_id: str
    timestamp: datetime
    result: AttemptResult
    phase_reached: int
    failure_move_id: str | None = None
