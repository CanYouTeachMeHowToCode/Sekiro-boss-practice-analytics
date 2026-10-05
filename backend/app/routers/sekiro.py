from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import models
from app.db.session import get_db
from app.models.analytics import SekiroAnalytics
from app.services import game_analytics_service

router = APIRouter(prefix="/api/sekiro", tags=["sekiro"])


@router.get("/analytics", response_model=SekiroAnalytics)
def get_sekiro_analytics(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return game_analytics_service.compute_sekiro_analytics(db, user.id)
