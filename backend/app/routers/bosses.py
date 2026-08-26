from fastapi import APIRouter, HTTPException

from app.models.boss import Boss, BossSummary
from app.services import boss_service

router = APIRouter(prefix="/api/bosses", tags=["bosses"])


@router.get("", response_model=list[BossSummary])
def list_bosses():
    return boss_service.get_all_bosses()


@router.get("/{boss_id}", response_model=Boss)
def get_boss(boss_id: str):
    boss = boss_service.get_boss(boss_id)
    if boss is None:
        raise HTTPException(status_code=404, detail=f"Boss '{boss_id}' not found")
    return boss
