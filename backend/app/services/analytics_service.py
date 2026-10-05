from collections import Counter

from sqlalchemy.orm import Session

from app.models.analytics import BossAnalytics, ProgressionPoint, RecentAnalytics
from app.models.attempt import Attempt, AttemptResult
from app.services import attempt_service

DEFAULT_RECENT_WINDOW = 10


def _failure_stats(attempts: list[Attempt]) -> dict:
    """Failure breakdowns for attempts ordered newest first; ties favor the more recent move."""
    failed = [a for a in attempts if a.result == AttemptResult.FAILED]
    by_phase = Counter(a.phase_reached for a in failed)
    by_move = Counter(a.failure_move_id for a in failed if a.failure_move_id)
    return {
        "main_bottleneck_phase": max(sorted(by_phase), key=lambda p: by_phase[p]) if by_phase else None,
        "most_common_failure_move": by_move.most_common(1)[0][0] if by_move else None,
        "failure_by_phase": {str(k): v for k, v in by_phase.items()},
        "failure_by_move": dict(by_move),
    }


def summarize(attempts: list[Attempt], recent_window: int = DEFAULT_RECENT_WINDOW) -> BossAnalytics:
    """Analytics for one boss's attempts, ordered newest first."""
    chronological = list(reversed(attempts))
    first_victory = next(
        (n for n, a in enumerate(chronological, start=1) if a.result == AttemptResult.VICTORY), None
    )
    recent = attempts[:recent_window]

    return BossAnalytics(
        total_attempts=len(attempts),
        defeated=first_victory is not None,
        best_phase=max((a.phase_reached for a in attempts), default=None),
        attempts_until_first_victory=first_victory,
        recent=RecentAnalytics(window_size=recent_window, total_attempts=len(recent), **_failure_stats(recent)),
        **_failure_stats(attempts),
    )


def progression(attempts: list[Attempt]) -> list[ProgressionPoint]:
    """Each attempt with its chronological number, oldest first, from attempts ordered newest first."""
    return [
        ProgressionPoint(
            attempt_number=n,
            attempt_id=a.id,
            timestamp=a.timestamp,
            result=a.result,
            phase_reached=a.phase_reached,
            failure_move_id=a.failure_move_id,
        )
        for n, a in enumerate(reversed(attempts), start=1)
    ]


def compute_analytics(
    session: Session, user_id: int, boss_id: str, recent_window: int = DEFAULT_RECENT_WINDOW
) -> BossAnalytics:
    return summarize(attempt_service.get_attempts(session, user_id, boss_id), recent_window)


def compute_progression(session: Session, user_id: int, boss_id: str) -> list[ProgressionPoint]:
    return progression(attempt_service.get_attempts(session, user_id, boss_id))
