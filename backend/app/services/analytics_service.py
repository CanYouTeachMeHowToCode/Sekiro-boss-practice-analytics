from collections import Counter

from app.models.analytics import BossAnalytics
from app.models.attempt import AttemptResult
from app.services import attempt_service


def compute_analytics(boss_id: str) -> BossAnalytics:
    attempts = attempt_service.get_attempts(boss_id)

    total_attempts = len(attempts)
    defeated = any(a.result == AttemptResult.VICTORY for a in attempts)
    best_phase = max((a.phase_reached for a in attempts), default=None)

    failed = [a for a in attempts if a.result == AttemptResult.FAILED]
    failure_by_phase = Counter(a.phase_reached for a in failed)
    failure_by_move = Counter(a.failure_move_id for a in failed if a.failure_move_id)

    main_bottleneck_phase = None
    if failure_by_phase:
        main_bottleneck_phase = max(
            sorted(failure_by_phase), key=lambda phase: failure_by_phase[phase]
        )

    most_common_failure_move = None
    if failure_by_move:
        most_common_failure_move = failure_by_move.most_common(1)[0][0]

    return BossAnalytics(
        total_attempts=total_attempts,
        defeated=defeated,
        best_phase=best_phase,
        main_bottleneck_phase=main_bottleneck_phase,
        most_common_failure_move=most_common_failure_move,
        failure_by_phase={str(k): v for k, v in failure_by_phase.items()},
        failure_by_move={str(k): v for k, v in failure_by_move.items()},
    )
