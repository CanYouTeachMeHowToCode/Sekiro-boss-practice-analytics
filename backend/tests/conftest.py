import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.seed import load_boss_data, sync_reference_data
from scripts.reset_test_database import reset_schema


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        if os.environ.get("REQUIRE_DATABASE_TESTS"):
            pytest.fail("REQUIRE_DATABASE_TESTS is set but TEST_DATABASE_URL is not")
        pytest.skip("TEST_DATABASE_URL is not set; skipping tests that need PostgreSQL")
    return url


@pytest.fixture(scope="session")
def engine(database_url):
    # Wipes the schema; reset_schema refuses unless the database name ends in '_test'.
    reset_schema(database_url)
    engine = create_engine(database_url)
    yield engine
    engine.dispose()


@pytest.fixture()
def session(engine):
    """A session whose changes, including commits, are rolled back after the test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def seeded_session(session):
    sync_reference_data(session, load_boss_data())
    return session


@pytest.fixture()
def anon_client(seeded_session):
    """A client that is not logged in."""
    app.dependency_overrides[get_db] = lambda: seeded_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client(anon_client):
    """A client logged in as a freshly registered user; the session cookie is kept between requests."""
    resp = anon_client.post("/api/auth/register", json={"username": "tester", "password": "correct-horse"})
    assert resp.status_code == 201, resp.text
    return anon_client
