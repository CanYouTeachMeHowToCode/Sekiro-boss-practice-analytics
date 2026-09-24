from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth import SESSION_COOKIE, clear_session_cookie, get_current_user, set_session_cookie
from app.db import models
from app.db.session import get_db
from app.models.auth import LoginRequest, RegisterRequest, User
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _to_response(user: models.User) -> User:
    return User(id=str(user.id), username=user.username)


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    try:
        user = auth_service.register_user(db, req.username, req.password)
    except auth_service.UsernameTakenError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    set_session_cookie(response, auth_service.create_session(db, user))
    return _to_response(user)


@router.post("/login", response_model=User)
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, req.username, req.password)
    if user is None:
        # Same message for an unknown user and a wrong password.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    set_session_cookie(response, auth_service.create_session(db, user))
    return _to_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
):
    if session_token:
        auth_service.end_session(db, session_token)
    clear_session_cookie(response)


@router.get("/me", response_model=User)
def me(user: models.User = Depends(get_current_user)):
    return _to_response(user)
