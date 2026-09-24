from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import models as db
from app.models.attempt import Attempt, AttemptResult, CreateAttemptRequest, FailureCategory
from app.services import boss_service


class AttemptValidationError(ValueError):
    pass


def _to_schema(row: db.Attempt, boss_slug: str) -> Attempt:
    return Attempt(
        id=str(row.id),
        boss_id=boss_slug,
        timestamp=row.created_at,
        result=AttemptResult(row.result),
        phase_reached=row.phase_reached,
        failure_move_id=row.failure_move.slug if row.failure_move else None,
        failure_category=FailureCategory(row.failure_category) if row.failure_category else None,
        notes=row.notes,
    )


def get_attempts(session: Session, user_id: int, boss_slug: str) -> list[Attempt]:
    """One user's attempts against one boss. Other users' and ownerless attempts are never included."""
    rows = session.scalars(
        select(db.Attempt)
        .join(db.Boss)
        .where(db.Attempt.user_id == user_id, db.Boss.slug == boss_slug)
        .options(selectinload(db.Attempt.failure_move))
        # Newest first. id breaks ties between attempts created in the same transaction.
        .order_by(db.Attempt.created_at.desc(), db.Attempt.id.desc())
    )
    return [_to_schema(row, boss_slug) for row in rows]


def create_attempt(session: Session, user_id: int, boss_slug: str, req: CreateAttemptRequest) -> Attempt:
    boss = boss_service.get_boss_row(session, boss_slug)
    if boss is None:
        raise AttemptValidationError(f"Boss '{boss_slug}' not found")

    failure_move = None
    failure_category = req.failure_category

    if req.result == AttemptResult.VICTORY:
        # A victory means the boss's final phase was cleared, regardless of
        # what phase the client sends - the client shouldn't need to know
        # (or be able to get wrong) which phase that is.
        phase_reached = boss_service.final_phase_number(session, boss.id)
        failure_category = None
    else:
        if req.phase_reached is None:
            raise AttemptValidationError("phase_reached is required for a failed attempt")
        if not boss_service.phase_exists(session, boss.id, req.phase_reached):
            raise AttemptValidationError(f"Phase {req.phase_reached} does not exist for boss '{boss_slug}'")
        phase_reached = req.phase_reached

        if req.failure_move_id is not None:
            failure_move = boss_service.get_move_row(session, boss.id, req.failure_move_id)
            if failure_move is None:
                raise AttemptValidationError(f"Move '{req.failure_move_id}' does not belong to boss '{boss_slug}'")
            if not boss_service.move_appears_in_phase(session, boss.id, phase_reached, failure_move.id):
                raise AttemptValidationError(
                    f"Move '{req.failure_move_id}' does not appear in phase {phase_reached} of boss '{boss_slug}'"
                )
            failure_category = None
        elif failure_category is None:
            failure_category = FailureCategory.NOT_SURE

    row = db.Attempt(
        boss=boss,
        user_id=user_id,
        result=req.result.value,
        phase_reached=phase_reached,
        failure_move=failure_move,
        failure_category=failure_category.value if failure_category else None,
        notes=req.notes or "",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_schema(row, boss_slug)
