"""Session cookie handling and the dependency that requires a logged-in user."""

import os

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.services import auth_service

SESSION_COOKIE = "session"


def _cookie_secure() -> bool:
    # Local development runs over plain HTTP, so Secure is opt-in until the
    # HTTPS deployment (V4 public deployment) sets COOKIE_SECURE=true.
    return os.environ.get("COOKIE_SECURE", "false").lower() == "true"


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(auth_service.SESSION_LIFETIME.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax", secure=_cookie_secure(), path="/")


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> User:
    user = auth_service.get_user_for_token(db, session_token) if session_token else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in")
    return user


def not_found() -> HTTPException:
    """FastAPI's own answer for a path that does not exist."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


def get_admin_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> User:
    """The logged-in admin. Anyone else, logged in or not, gets the 404 of a path that does not exist, so the admin
    endpoints give nothing away."""
    user = auth_service.get_user_for_token(db, session_token) if session_token else None
    if user is None or not user.is_admin:
        raise not_found()
    return user
