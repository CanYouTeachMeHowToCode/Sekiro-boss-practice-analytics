from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import models as db
from app.models.boss import Boss, BossMove, BossPhase, BossSummary


def get_all_bosses(session: Session) -> list[BossSummary]:
    rows = session.scalars(select(db.Boss).order_by(db.Boss.id))
    return [BossSummary(id=b.slug, name=b.name, name_zh=b.name_zh, location=b.location) for b in rows]


def get_boss_row(session: Session, boss_slug: str) -> db.Boss | None:
    return session.scalar(select(db.Boss).where(db.Boss.slug == boss_slug))


def get_boss(session: Session, boss_slug: str) -> Boss | None:
    boss = session.scalar(
        select(db.Boss)
        .where(db.Boss.slug == boss_slug)
        .options(
            selectinload(db.Boss.game),
            selectinload(db.Boss.phases).selectinload(db.BossPhase.move_links).selectinload(db.PhaseMove.move),
        )
    )
    if boss is None:
        return None
    return Boss(
        id=boss.slug,
        name=boss.name,
        name_zh=boss.name_zh,
        game=boss.game.slug,
        location=boss.location,
        source_name=boss.source_name,
        source_url=boss.source_url,
        phases=[
            BossPhase(
                phase_number=phase.phase_number,
                name=phase.name,
                moves=[
                    BossMove(
                        id=link.move.slug,
                        name=link.move.name,
                        move_type=link.move.move_type,
                        description=link.move.description,
                        telegraph=link.move.telegraph,
                        counter=link.move.counter,
                        common_mistakes=link.move.common_mistakes,
                    )
                    for link in phase.move_links
                ],
            )
            for phase in boss.phases
        ],
    )


def get_move_row(session: Session, boss_id: int, move_slug: str) -> db.Move | None:
    return session.scalar(select(db.Move).where(db.Move.boss_id == boss_id, db.Move.slug == move_slug))


def phase_exists(session: Session, boss_id: int, phase_number: int) -> bool:
    return (
        session.scalar(
            select(db.BossPhase.id).where(db.BossPhase.boss_id == boss_id, db.BossPhase.phase_number == phase_number)
        )
        is not None
    )


def move_appears_in_phase(session: Session, boss_id: int, phase_number: int, move_id: int) -> bool:
    return (
        session.scalar(
            select(db.PhaseMove.move_id)
            .join(db.BossPhase)
            .where(
                db.BossPhase.boss_id == boss_id,
                db.BossPhase.phase_number == phase_number,
                db.PhaseMove.move_id == move_id,
            )
        )
        is not None
    )


def final_phase_number(session: Session, boss_id: int) -> int:
    return session.scalar(select(func.max(db.BossPhase.phase_number)).where(db.BossPhase.boss_id == boss_id))
