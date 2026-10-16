import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import session as db_session
from app.db.base import Base
from app.db.models import Attempt, Boss, BossPhase, Game, Move, PhaseMove, User
from scripts.claim_attempts import claim_attempts
from scripts.reset_test_database import alembic_config

APP_TABLES = {"games", "bosses", "boss_phases", "moves", "phase_moves", "attempts", "users", "user_sessions"}
BEFORE_NOT_NULL = "5bc59c89a1b6"  # the revision before attempts.user_id becomes NOT NULL


def make_boss(session: Session, slug: str = "owl-father") -> Boss:
    game = session.query(Game).filter_by(slug="sekiro").one_or_none()
    if game is None:
        game = Game(slug="sekiro", name="Sekiro: Shadows Die Twice")
    boss = Boss(game=game, slug=slug, name=slug.title(), location="Somewhere")
    session.add(boss)
    session.flush()
    return boss


def make_user(session: Session, username: str = "wolf") -> User:
    user = User(username=username, password_hash="not-a-real-hash")
    session.add(user)
    session.flush()
    return user


def remove_mig_rows(engine) -> None:
    """Deletes what the migration tests insert: everything under the 'mig' game, and the 'mig-' users."""
    bosses = "(SELECT id FROM bosses WHERE game_id IN (SELECT id FROM games WHERE slug = 'mig'))"
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM attempts WHERE boss_id IN {bosses}"))
        conn.execute(text(f"DELETE FROM moves WHERE boss_id IN {bosses}"))
        conn.execute(text(f"DELETE FROM boss_phases WHERE boss_id IN {bosses}"))
        conn.execute(text(f"DELETE FROM bosses WHERE id IN {bosses}"))
        conn.execute(text("DELETE FROM games WHERE slug = 'mig'"))
        conn.execute(text("DELETE FROM users WHERE username LIKE 'mig-%'"))


def test_migration_creates_expected_tables(engine):
    tables = set(inspect(engine).get_table_names())
    assert APP_TABLES <= tables


def test_models_match_the_migrations(engine):
    """Fails when models.py changes without a matching Alembic migration."""
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)

    assert differences == [], (
        "The SQLAlchemy models and the migrations have drifted apart. "
        "Generate a migration with `alembic revision --autogenerate` and review it."
    )


def test_migration_can_downgrade_and_upgrade_again(engine, database_url):
    config = alembic_config(database_url)
    command.downgrade(config, "base")
    assert not APP_TABLES & set(inspect(engine).get_table_names())
    command.upgrade(config, "head")
    assert APP_TABLES <= set(inspect(engine).get_table_names())


def test_adding_attempt_owners_keeps_existing_attempts_as_ownerless(engine, database_url):
    """Upgrading a database that already has V2 attempts must not drop or reassign them."""
    config = alembic_config(database_url)
    command.downgrade(config, "980c7a879ddb")  # the revision before attempts.user_id
    try:
        with engine.begin() as conn:
            game_id = conn.scalar(text("INSERT INTO games (slug, name) VALUES ('mig', 'Mig') RETURNING id"))
            boss_id = conn.scalar(
                text("INSERT INTO bosses (game_id, slug, name, location) VALUES (:g, 'mig-boss', 'M', 'L') RETURNING id"),
                {"g": game_id},
            )
            conn.execute(
                text("INSERT INTO attempts (boss_id, result, phase_reached) VALUES (:b, 'failed', 1)"), {"b": boss_id}
            )

        command.upgrade(config, BEFORE_NOT_NULL)

        with engine.connect() as conn:
            rows = conn.execute(text("SELECT user_id FROM attempts WHERE boss_id = :b"), {"b": boss_id}).all()
        assert rows == [(None,)]
    finally:
        remove_mig_rows(engine)
        command.upgrade(config, "head")


def test_way_of_tomoe_migration_moves_isshin_attempts_up_one_phase(engine, database_url):
    config = alembic_config(database_url)
    command.downgrade(config, "6849ddf003e3")  # the revision before the shift
    try:
        with engine.begin() as conn:
            game_id = conn.scalar(text("INSERT INTO games (slug, name) VALUES ('mig', 'Mig') RETURNING id"))
            ids = {}
            for slug in ("isshin-sword-saint", "mig-other-boss"):
                ids[slug] = conn.scalar(
                    text("INSERT INTO bosses (game_id, slug, name, location) VALUES (:g, :s, 'B', 'L') RETURNING id"),
                    {"g": game_id, "s": slug},
                )
                conn.execute(
                    text("INSERT INTO attempts (boss_id, result, phase_reached) VALUES (:b, 'failed', 2)"),
                    {"b": ids[slug]},
                )

        command.upgrade(config, BEFORE_NOT_NULL)

        with engine.connect() as conn:
            phases = dict(conn.execute(text("SELECT b.slug, a.phase_reached FROM attempts a JOIN bosses b ON b.id = a.boss_id")).all())
        assert phases == {"isshin-sword-saint": 3, "mig-other-boss": 2}
    finally:
        remove_mig_rows(engine)
        command.upgrade(config, "head")


def test_iaijutsu_migration_moves_its_attempts_to_receding_tide(engine, database_url):
    config = alembic_config(database_url)
    command.downgrade(config, "76532dd774e5")  # the revision before the merge
    try:
        with engine.begin() as conn:
            game_id = conn.scalar(text("INSERT INTO games (slug, name) VALUES ('mig', 'Mig') RETURNING id"))
            boss_id = conn.scalar(
                text("INSERT INTO bosses (game_id, slug, name, location) VALUES (:g, 'genichiro-ashina', 'G', 'L') RETURNING id"),
                {"g": game_id},
            )
            phase_id = conn.scalar(
                text("INSERT INTO boss_phases (boss_id, phase_number, name) VALUES (:b, 1, 'Phase 1') RETURNING id"),
                {"b": boss_id},
            )
            moves = {}
            for slug in ("iaijutsu", "receding-tide", "hawk-shot"):
                moves[slug] = conn.scalar(
                    text("INSERT INTO moves (boss_id, slug, name, move_type) VALUES (:b, :s, :s, 'combo') RETURNING id"),
                    {"b": boss_id, "s": slug},
                )
                conn.execute(
                    text("INSERT INTO phase_moves (boss_phase_id, move_id, position) VALUES (:p, :m, :n)"),
                    {"p": phase_id, "m": moves[slug], "n": len(moves)},
                )
            user_id = conn.scalar(text("INSERT INTO users (username, password_hash) VALUES ('mig-wolf', 'x') RETURNING id"))
            for slug in ("iaijutsu", "iaijutsu", "hawk-shot"):
                conn.execute(
                    text(
                        "INSERT INTO attempts (boss_id, user_id, result, phase_reached, failure_move_id) "
                        "VALUES (:b, :u, 'failed', 1, :m)"
                    ),
                    {"b": boss_id, "u": user_id, "m": moves[slug]},
                )

        command.upgrade(config, "head")

        with engine.connect() as conn:
            failures = conn.execute(
                text(
                    "SELECT m.slug FROM attempts a JOIN moves m ON m.id = a.failure_move_id "
                    "WHERE a.boss_id = :b ORDER BY m.slug"
                ),
                {"b": boss_id},
            ).scalars().all()
            remaining = conn.execute(
                text("SELECT slug FROM moves WHERE boss_id = :b ORDER BY slug"), {"b": boss_id}
            ).scalars().all()
            links = conn.scalar(text("SELECT count(*) FROM phase_moves WHERE boss_phase_id = :p"), {"p": phase_id})
        assert failures == ["hawk-shot", "receding-tide", "receding-tide"]
        assert remaining == ["hawk-shot", "receding-tide"]
        assert links == 2
    finally:
        remove_mig_rows(engine)
        command.upgrade(config, "head")


def user_id_is_nullable(engine) -> bool:
    with engine.connect() as conn:
        return conn.scalar(
            text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_name = 'attempts' AND column_name = 'user_id'"
            )
        ) == "YES"


def test_not_null_owner_migration_waits_until_every_attempt_is_claimed(engine, database_url):
    config = alembic_config(database_url)
    command.downgrade(config, BEFORE_NOT_NULL)
    try:
        with engine.begin() as conn:
            game_id = conn.scalar(text("INSERT INTO games (slug, name) VALUES ('mig', 'Mig') RETURNING id"))
            boss_id = conn.scalar(
                text("INSERT INTO bosses (game_id, slug, name, location) VALUES (:g, 'mig-boss', 'M', 'L') RETURNING id"),
                {"g": game_id},
            )
            owner_id = conn.scalar(text("INSERT INTO users (username, password_hash) VALUES ('mig-owner', 'x') RETURNING id"))
            other_id = conn.scalar(text("INSERT INTO users (username, password_hash) VALUES ('mig-other', 'x') RETURNING id"))
            conn.execute(
                text(
                    "INSERT INTO attempts (boss_id, user_id, result, phase_reached) "
                    "VALUES (:b, NULL, 'failed', 1), (:b, NULL, 'failed', 2), (:b, :o, 'failed', 1)"
                ),
                {"b": boss_id, "o": other_id},
            )

        with pytest.raises(RuntimeError, match="2 attempt"):
            command.upgrade(config, "head")
        assert user_id_is_nullable(engine)

        with Session(engine) as session:
            assert claim_attempts(session, "mig-owner") == 2
        command.upgrade(config, "head")

        with engine.connect() as conn:
            owners = conn.execute(text("SELECT user_id FROM attempts WHERE boss_id = :b"), {"b": boss_id}).scalars().all()
        assert sorted(owners) == sorted([owner_id, owner_id, other_id])
        assert not user_id_is_nullable(engine)
    finally:
        remove_mig_rows(engine)
        command.upgrade(config, "head")


def test_move_source_name_and_url_go_together(session):
    boss = make_boss(session)
    session.add(Move(boss=boss, slug="half-source", name="X", move_type="thrust", source_name="Somewhere"))
    with pytest.raises(IntegrityError):
        session.flush()


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
    attempt = Attempt(boss=boss, user=make_user(session), result="failed", phase_reached=1, failure_category="not_sure")
    session.add(attempt)
    session.flush()
    session.refresh(attempt)

    assert isinstance(attempt.id, int)
    assert attempt.failure_move_id is None
    assert attempt.notes == ""
    assert attempt.created_at is not None


def test_attempt_can_reference_a_known_move(session):
    boss, user = make_boss(session), make_user(session)
    move = Move(boss=boss, slug="shadowfall", name="Shadowfall", move_type="thrust")
    session.add(Attempt(boss=boss, user=user, result="failed", phase_reached=2, failure_move=move))
    session.flush()

    attempt = session.query(Attempt).one()
    assert attempt.failure_move.slug == "shadowfall"


def test_attempt_must_reference_an_existing_boss(session):
    session.add(Attempt(boss_id=999_999, user=make_user(session), result="victory", phase_reached=1))
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
    session.add(Attempt(boss=boss, user=make_user(session), phase_reached=1, **fields))
    with pytest.raises(IntegrityError):
        session.flush()


def test_attempt_cannot_have_both_a_failure_move_and_a_category(session):
    boss, user = make_boss(session), make_user(session)
    move = Move(boss=boss, slug="shadowfall", name="Shadowfall", move_type="thrust")
    session.add(Attempt(boss=boss, user=user, result="failed", phase_reached=1, failure_move=move, failure_category="other"))
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
