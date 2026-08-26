from pydantic import BaseModel


class BossAnalytics(BaseModel):
    total_attempts: int
    defeated: bool
    best_phase: int | None = None
    main_bottleneck_phase: int | None = None
    most_common_failure_move: str | None = None
    failure_by_phase: dict[str, int] = {}
    failure_by_move: dict[str, int] = {}
