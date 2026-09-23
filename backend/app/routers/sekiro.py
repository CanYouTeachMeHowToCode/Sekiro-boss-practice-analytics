from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.analytics import SekiroAnalytics
from app.services import game_analytics_service

router = APIRouter(prefix="/api/sekiro", tags=["sekiro"])


@router.get("/analytics", response_model=SekiroAnalytics)
def get_sekiro_analytics(db: Session = Depends(get_db)):
    return game_analytics_service.compute_sekiro_analytics(db)
