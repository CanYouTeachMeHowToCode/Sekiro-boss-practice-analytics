import os

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from tests.db.alembic_helpers import alembic_config


def _test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        return url
    if os.environ.get("REQUIRE_DATABASE_TESTS"):
        pytest.fail("REQUIRE_DATABASE_TESTS is set but TEST_DATABASE_URL is not")
    pytest.skip("TEST_DATABASE_URL is not set; skipping PostgreSQL tests")


def _ensure_database_exists(url: str) -> None:
    parsed = make_url(url)
    admin = create_engine(parsed.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": parsed.database}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{parsed.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def database_url() -> str:
    url = _test_database_url()
    # These tests wipe the schema, so refuse to touch anything that isn't
    # clearly a throwaway test database.
    if not make_url(url).database.endswith("_test"):
        pytest.fail(f"TEST_DATABASE_URL must point at a database ending in '_test', got {url!r}")
    _ensure_database_exists(url)
    return url


@pytest.fixture(scope="session")
def engine(database_url):
    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config(database_url), "head")
    yield engine
    engine.dispose()


@pytest.fixture()
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()
