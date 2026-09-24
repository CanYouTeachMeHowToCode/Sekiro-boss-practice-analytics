from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.auth import SESSION_COOKIE
from app.db.models import User, UserSession

CREDENTIALS = {"username": "wolf", "password": "kusabimaru"}


def register(client, **overrides):
    return client.post("/api/auth/register", json={**CREDENTIALS, **overrides})


def test_register_logs_the_user_in_with_an_httponly_cookie(anon_client):
    resp = register(anon_client)

    assert resp.status_code == 201
    assert resp.json()["username"] == "wolf"
    set_cookie = resp.headers["set-cookie"].lower()
    assert f"{SESSION_COOKIE}=" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert anon_client.get("/api/auth/me").json()["username"] == "wolf"


def test_username_is_case_insensitive_and_stored_lowercase(anon_client):
    assert register(anon_client, username="  Wolf ").json()["username"] == "wolf"

    resp = register(anon_client, username="WOLF")
    assert resp.status_code == 409


@pytest.mark.parametrize(
    "overrides",
    [
        {"username": "ab"},
        {"username": "has space"},
        {"username": "x" * 31},
        {"password": "short"},
        {"password": "p" * 129},
    ],
    ids=["username-too-short", "username-bad-characters", "username-too-long", "password-too-short", "password-too-long"],
)
def test_register_rejects_invalid_input(anon_client, overrides):
    assert register(anon_client, **overrides).status_code == 422


def test_passwords_and_session_tokens_are_stored_hashed(anon_client, seeded_session):
    register(anon_client)
    token = anon_client.cookies[SESSION_COOKIE]

    user = seeded_session.scalar(select(User).where(User.username == "wolf"))
    assert user.password_hash.startswith("$argon2")
    assert CREDENTIALS["password"] not in user.password_hash
    stored = seeded_session.scalars(select(UserSession.token_hash)).all()
    assert token not in stored


def test_login_with_correct_password(anon_client):
    register(anon_client)
    anon_client.cookies.clear()

    resp = anon_client.post("/api/auth/login", json={"username": "WOLF", "password": "kusabimaru"})

    assert resp.status_code == 200
    assert anon_client.get("/api/auth/me").status_code == 200


@pytest.mark.parametrize(
    "credentials",
    [{"username": "wolf", "password": "wrong-password"}, {"username": "nobody", "password": "kusabimaru"}],
    ids=["wrong-password", "unknown-user"],
)
def test_login_failures_give_the_same_answer(anon_client, credentials):
    register(anon_client)
    anon_client.cookies.clear()

    resp = anon_client.post("/api/auth/login", json=credentials)

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Incorrect username or password"
    assert SESSION_COOKIE not in anon_client.cookies


def test_logout_ends_the_session_on_the_server(anon_client):
    register(anon_client)
    token = anon_client.cookies[SESSION_COOKIE]

    assert anon_client.post("/api/auth/logout").status_code == 204

    # Replaying the old cookie must not work once the session is gone.
    anon_client.cookies.set(SESSION_COOKIE, token)
    assert anon_client.get("/api/auth/me").status_code == 401


def test_expired_session_is_rejected_and_removed(anon_client, seeded_session):
    register(anon_client)
    session = seeded_session.scalar(select(UserSession))
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    seeded_session.commit()

    assert anon_client.get("/api/auth/me").status_code == 401
    assert seeded_session.scalar(select(UserSession)) is None


def test_unknown_session_token_is_rejected(anon_client):
    anon_client.cookies.set(SESSION_COOKIE, "made-up-token")
    assert anon_client.get("/api/auth/me").status_code == 401


def test_boss_data_is_public(anon_client):
    assert anon_client.get("/api/bosses").status_code == 200
    assert anon_client.get("/api/bosses/genichiro-ashina").status_code == 200


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/api/bosses/genichiro-ashina/attempts"),
        ("post", "/api/bosses/genichiro-ashina/attempts"),
        ("get", "/api/bosses/genichiro-ashina/analytics"),
        ("get", "/api/bosses/genichiro-ashina/progression"),
        ("get", "/api/sekiro/analytics"),
    ],
)
def test_attempts_and_analytics_require_login(anon_client, method, path):
    kwargs = {"json": {"result": "victory"}} if method == "post" else {}
    assert getattr(anon_client, method)(path, **kwargs).status_code == 401
