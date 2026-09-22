import pytest
from alembic import command
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import session as db_session
from app.db.models import Attempt, Boss, BossPhase, Game, Move, PhaseMove
from scripts.reset_test_database import alembic_config

APP_TABLES = {"games", "bosses", "boss_phases", "moves", "phase_moves", "attempts"}


def make_boss(session: Session, slug: str = "owl-father") -> Boss:
    game = session.query(Game).filter_by(slug="sekiro").one_or_none()
    if game is None:
        game = Game(slug="sekiro", name="Sekiro: Shadows Die Twice")
    boss = Boss(game=game, slug=slug, name=slug.title(), location="Somewhere")
    session.add(boss)
    session.flush()
    return boss


def test_migration_creates_expected_tables(engine):
    tables = set(inspect(engine).get_table_names())
    assert APP_TABLES <= tables


def test_migration_can_downgrade_and_upgrade_again(engine, database_url):
    config = alembic_config(database_url)
    command.downgrade(config, "base")
    assert not APP_TABLES & set(inspect(engine).get_table_names())
    command.upgrade(config, "head")
    assert APP_TABLES <= set(inspect(engine).get_table_names())


def test_move_is_stored_once_and_shared_across_phases(session):
    boss = make_boss(session)
    phase_1 = BossPhase(boss=boss, phase_number=1, name="Phase 1")
    phase_2 = BossPhase(boss=boss, phase_number=2, name="Phase 2")
    shadowfall = Move(boss=boss, slug="shadowfall", name="Shadowfall", move_type="thrust")
    teleport = Move(boss=boss, slug="owl-teleport", name="Owl Teleport", move_type="teleport")
    phase_1.move_links.append(PhaseMove(move=shadowfall, position=0))
    # Added out of order to check that position, not insertion order, decides the order.
    phase_2.move_links.extend([PhaseMove(move=teleport, position=1), PhaseMove(move=shadowfall, position=0)])
    session.add_all([phase_1, phase_2])
    session.flush()
    session.expire_all()

    reloaded = session.get(Boss, boss.id)
    assert [p.phase_number for p in reloaded.phases] == [1, 2]
    assert [link.move.slug for link in reloaded.phases[0].move_links] == ["shadowfall"]
    assert [link.move.slug for link in reloaded.phases[1].move_links] == ["shadowfall", "owl-teleport"]
    assert session.query(Move).filter_by(boss_id=boss.id, slug="shadowfall").count() == 1


def test_move_slug_is_unique_within_a_boss_but_not_across_bosses(session):
    owl = make_boss(session, "owl-father")
    monk = make_boss(session, "corrupted-monk")
    session.add_all(
        [
            Move(boss=owl, slug="thrust-attack", name="Thrust", move_type="thrust"),
            Move(boss=monk, slug="thrust-attack", name="Thrust", move_type="thrust"),
        ]
    )
    session.flush()

    session.add(Move(boss=owl, slug="thrust-attack", name="Duplicate", move_type="thrust"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_phase_number_is_unique_within_a_boss(session):
    boss = make_boss(session)
    session.add_all(
        [
            BossPhase(boss=boss, phase_number=1, name="Phase 1"),
            BossPhase(boss=boss, phase_number=1, name="Phase 1 again"),
        ]
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_attempt_persists_with_nullable_failure_move(session):
    boss = make_boss(session)
    attempt = Attempt(boss=boss, result="failed", phase_reached=1, failure_category="not_sure")
    session.add(attempt)
    session.flush()
    session.refresh(attempt)

    assert isinstance(attempt.id, int)
    assert attempt.failure_move_id is None
    assert attempt.notes == ""
    assert attempt.created_at is not None


def test_attempt_can_reference_a_known_move(session):
    boss = make_boss(session)
    move = Move(boss=boss, slug="shadowfall", name="Shadowfall", move_type="thrust")
    session.add(Attempt(boss=boss, result="failed", phase_reached=2, failure_move=move))
    session.flush()

    attempt = session.query(Attempt).one()
    assert attempt.failure_move.slug == "shadowfall"


def test_attempt_must_reference_an_existing_boss(session):
    session.add(Attempt(boss_id=999_999, result="victory", phase_reached=1))
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize(
    "fields",
    [
        {"result": "draw"},
        {"result": "failed", "failure_category": "unknown"},
        {"result": "victory", "failure_category": "not_sure"},
    ],
    ids=["invalid-result", "invalid-category", "victory-with-failure-cause"],
)
def test_attempt_check_constraints(session, fields):
    boss = make_boss(session)
    session.add(Attempt(boss=boss, phase_reached=1, **fields))
    with pytest.raises(IntegrityError):
        session.flush()


def test_attempt_cannot_have_both_a_failure_move_and_a_category(session):
    boss = make_boss(session)
    move = Move(boss=boss, slug="shadowfall", name="Shadowfall", move_type="thrust")
    session.add(
        Attempt(boss=boss, result="failed", phase_reached=1, failure_move=move, failure_category="other")
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_fastapi_dependency_reaches_postgres(engine, database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", database_url)
    db_session.get_engine.cache_clear()
    db_session.get_sessionmaker.cache_clear()

    app = FastAPI()

    @app.get("/db-check")
    def db_check(db: Session = Depends(db_session.get_db)):
        return {"tables": db.execute(text("SELECT count(*) FROM games")).scalar_one() >= 0}

    try:
        resp = TestClient(app).get("/db-check")
    finally:
        db_session.get_engine().dispose()
        db_session.get_engine.cache_clear()
        db_session.get_sessionmaker.cache_clear()

    assert resp.status_code == 200
    assert resp.json() == {"tables": True}
