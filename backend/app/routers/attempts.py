from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.analytics import BossAnalytics, ProgressionPoint
from app.models.attempt import Attempt, CreateAttemptRequest
from app.services import analytics_service, attempt_service, boss_service

router = APIRouter(prefix="/api/bosses/{boss_id}", tags=["attempts"])


def _ensure_boss_exists(db: Session, boss_id: str) -> None:
    if boss_service.get_boss_row(db, boss_id) is None:
        raise HTTPException(status_code=404, detail=f"Boss '{boss_id}' not found")


@router.post("/attempts", response_model=Attempt, status_code=status.HTTP_201_CREATED)
def create_attempt(boss_id: str, req: CreateAttemptRequest, db: Session = Depends(get_db)):
    _ensure_boss_exists(db, boss_id)
    try:
        return attempt_service.create_attempt(db, boss_id, req)
    except attempt_service.AttemptValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/attempts", response_model=list[Attempt])
def list_attempts(boss_id: str, db: Session = Depends(get_db)):
    _ensure_boss_exists(db, boss_id)
    return attempt_service.get_attempts(db, boss_id)


@router.get("/analytics", response_model=BossAnalytics)
def get_analytics(
    boss_id: str,
    recent: int = Query(
        analytics_service.DEFAULT_RECENT_WINDOW,
        ge=1,
        le=100,
        description="How many of the most recent attempts to compare against the full history.",
    ),
    db: Session = Depends(get_db),
):
    _ensure_boss_exists(db, boss_id)
    return analytics_service.compute_analytics(db, boss_id, recent)


@router.get("/progression", response_model=list[ProgressionPoint])
def get_progression(boss_id: str, db: Session = Depends(get_db)):
    _ensure_boss_exists(db, boss_id)
    return analytics_service.compute_progression(db, boss_id)
