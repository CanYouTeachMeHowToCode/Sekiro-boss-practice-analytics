from fastapi import APIRouter, HTTPException, status

from app.models.analytics import BossAnalytics
from app.models.attempt import Attempt, CreateAttemptRequest
from app.services import analytics_service, attempt_service, boss_service

router = APIRouter(prefix="/api/bosses/{boss_id}", tags=["attempts"])


def _ensure_boss_exists(boss_id: str) -> None:
    if boss_service.get_boss(boss_id) is None:
        raise HTTPException(status_code=404, detail=f"Boss '{boss_id}' not found")


@router.post("/attempts", response_model=Attempt, status_code=status.HTTP_201_CREATED)
def create_attempt(boss_id: str, req: CreateAttemptRequest):
    _ensure_boss_exists(boss_id)
    try:
        return attempt_service.create_attempt(boss_id, req)
    except attempt_service.AttemptValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/attempts", response_model=list[Attempt])
def list_attempts(boss_id: str):
    _ensure_boss_exists(boss_id)
    return attempt_service.get_attempts(boss_id)


@router.get("/analytics", response_model=BossAnalytics)
def get_analytics(boss_id: str):
    _ensure_boss_exists(boss_id)
    return analytics_service.compute_analytics(boss_id)
