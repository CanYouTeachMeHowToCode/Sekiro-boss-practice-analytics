"""Accounts, password hashing and login sessions.

Sessions are stored server-side so logging out really ends them. The cookie
holds a random token; the database only keeps its SHA-256 hash, so a leaked
database does not leak usable session tokens.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import User, UserSession

SESSION_LIFETIME = timedelta(days=30)

_hasher = PasswordHasher()


class UsernameTakenError(Exception):
    pass


def normalize_username(username: str) -> str:
    return username.strip().lower()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == normalize_username(username)))


def register_user(db: Session, username: str, password: str) -> User:
    username = normalize_username(username)
    if get_user_by_username(db, username) is not None:
        raise UsernameTakenError(f"Username '{username}' is already taken")
    user = User(username=username, password_hash=_hasher.hash(password))
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if user is None:
        return None
    try:
        _hasher.verify(user.password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return None
    if _hasher.check_needs_rehash(user.password_hash):
        user.password_hash = _hasher.hash(password)
        db.commit()
    return user


def create_session(db: Session, user: User) -> str:
    """Starts a session for the user and returns the raw token for the cookie."""
    db.execute(delete(UserSession).where(UserSession.user_id == user.id, UserSession.expires_at <= _now()))
    token = secrets.token_urlsafe(32)
    db.add(UserSession(user_id=user.id, token_hash=_hash_token(token), expires_at=_now() + SESSION_LIFETIME))
    db.commit()
    return token


def get_user_for_token(db: Session, token: str) -> User | None:
    session = db.scalar(select(UserSession).where(UserSession.token_hash == _hash_token(token)))
    if session is None:
        return None
    if session.expires_at <= _now():
        db.delete(session)
        db.commit()
        return None
    return session.user


def end_session(db: Session, token: str) -> None:
    db.execute(delete(UserSession).where(UserSession.token_hash == _hash_token(token)))
    db.commit()
