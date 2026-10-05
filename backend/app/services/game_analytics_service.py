"""Game-level analytics across every Sekiro boss, for one user's attempts."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db import models as db
from app.models.analytics import BossComparisonRow, RecentAttempt, SekiroAnalytics
from app.models.attempt import AttemptResult, FailureCategory

RECENT_WINDOW_DAYS = 7
RECENT_ATTEMPTS_LIMIT = 10


def _boss_rows(session: Session, user_id: int) -> list[BossComparisonRow]:
    """One row per boss, computed with grouped queries rather than a query per boss."""
    phase_counts = (
        select(db.BossPhase.boss_id, func.count().label("total_phases")).group_by(db.BossPhase.boss_id).subquery()
    )
    attempt_stats = (
        select(
            db.Attempt.boss_id,
            func.count().label("attempts"),
            func.max(db.Attempt.phase_reached).label("best_phase"),
            func.bool_or(db.Attempt.result == AttemptResult.VICTORY.value).label("defeated"),
            func.max(db.Attempt.created_at).label("last_attempt_at"),
        )
        .where(db.Attempt.user_id == user_id)
        .group_by(db.Attempt.boss_id)
        .subquery()
    )
    # Number each boss's attempts chronologically, then take the number of its first victory.
    numbered = (
        select(
            db.Attempt.boss_id,
            db.Attempt.result,
            func.row_number()
            .over(partition_by=db.Attempt.boss_id, order_by=(db.Attempt.created_at, db.Attempt.id))
            .label("attempt_number"),
        )
        .where(db.Attempt.user_id == user_id)
        .subquery()
    )
    first_victory = (
        select(
            numbered.c.boss_id,
            func.min(
                case((numbered.c.result == AttemptResult.VICTORY.value, numbered.c.attempt_number))
            ).label("attempts_until_first_victory"),
        )
        .group_by(numbered.c.boss_id)
        .subquery()
    )

    rows = session.execute(
        select(
            db.Boss.slug,
            db.Boss.name,
            db.Boss.name_zh,
            func.coalesce(phase_counts.c.total_phases, 0),
            func.coalesce(attempt_stats.c.attempts, 0),
            attempt_stats.c.best_phase,
            func.coalesce(attempt_stats.c.defeated, False),
            first_victory.c.attempts_until_first_victory,
            attempt_stats.c.last_attempt_at,
        )
        .outerjoin(phase_counts, phase_counts.c.boss_id == db.Boss.id)
        .outerjoin(attempt_stats, attempt_stats.c.boss_id == db.Boss.id)
        .outerjoin(first_victory, first_victory.c.boss_id == db.Boss.id)
        .order_by(db.Boss.id)
    )
    return [
        BossComparisonRow(
            id=slug,
            name=name,
            name_zh=name_zh,
            total_phases=total_phases,
            attempts=attempts,
            best_phase=best_phase,
            defeated=defeated,
            attempts_until_first_victory=first,
            last_attempt_at=last,
        )
        for slug, name, name_zh, total_phases, attempts, best_phase, defeated, first, last in rows
    ]


def _recent_attempts(session: Session, user_id: int) -> list[RecentAttempt]:
    rows = session.execute(
        select(db.Attempt, db.Boss.slug, db.Boss.name, db.Boss.name_zh, db.Move.slug, db.Move.name, db.Move.name_zh)
        .join(db.Boss, db.Attempt.boss_id == db.Boss.id)
        .outerjoin(db.Move, db.Attempt.failure_move_id == db.Move.id)
        .where(db.Attempt.user_id == user_id)
        .order_by(db.Attempt.created_at.desc(), db.Attempt.id.desc())
        .limit(RECENT_ATTEMPTS_LIMIT)
    )
    return [
        RecentAttempt(
            attempt_id=str(attempt.id),
            boss_id=boss_slug,
            boss_name=boss_name,
            boss_name_zh=boss_name_zh,
            timestamp=attempt.created_at,
            result=AttemptResult(attempt.result),
            phase_reached=attempt.phase_reached,
            failure_move_id=move_slug,
            failure_move_name=move_name,
            failure_move_name_zh=move_name_zh,
            failure_category=FailureCategory(attempt.failure_category) if attempt.failure_category else None,
        )
        for attempt, boss_slug, boss_name, boss_name_zh, move_slug, move_name, move_name_zh in rows
    ]


def _ids_with_max(rows: list[BossComparisonRow], value) -> list[str]:
    values = [value(r) for r in rows if value(r) is not None]
    if not values:
        return []
    top = max(values)
    return [r.id for r in rows if value(r) == top]


def compute_sekiro_analytics(session: Session, user_id: int, now: datetime | None = None) -> SekiroAnalytics:
    now = now or datetime.now(timezone.utc)
    bosses = _boss_rows(session, user_id)
    attempted = [b for b in bosses if b.attempts > 0]
    defeated = [b for b in bosses if b.defeated]
    in_window = session.scalar(
        select(func.count())
        .select_from(db.Attempt)
        .where(db.Attempt.user_id == user_id, db.Attempt.created_at >= now - timedelta(days=RECENT_WINDOW_DAYS))
    )

    return SekiroAnalytics(
        total_bosses=len(bosses),
        bosses_attempted=len(attempted),
        bosses_defeated=len(defeated),
        total_attempts=sum(b.attempts for b in bosses),
        most_practiced_bosses=_ids_with_max(attempted, lambda b: b.attempts),
        most_attempts_to_defeat=max((b.attempts_until_first_victory for b in defeated), default=None),
        bosses_requiring_most_attempts=_ids_with_max(defeated, lambda b: b.attempts_until_first_victory),
        recent_window_days=RECENT_WINDOW_DAYS,
        attempts_in_recent_window=in_window,
        recent_attempts=_recent_attempts(session, user_id),
        bosses=bosses,
    )
