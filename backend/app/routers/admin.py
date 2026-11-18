import logging

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import get_admin_user, not_found
from app.db import models
from app.db.session import get_db
from app.models.recording import AdminRecording, AdminRecordingReport
from app.services import admin_service

# The read-only admin view (owner decision, 2026-11-18): GET only. For anyone but an admin every path here is a 404,
# exactly like a path that does not exist.
router = APIRouter(prefix="/api/admin", tags=["admin"])

log = logging.getLogger("app.admin")


@router.get("/recordings", response_model=list[AdminRecording])
def list_recordings(admin: models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return admin_service.list_recordings(db)


@router.get("/recordings/{recording_id}", response_model=AdminRecordingReport)
def get_report(recording_id: str, admin: models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    report = admin_service.get_report(db, recording_id)
    if report is None:
        raise not_found()
    log.info("admin %s viewed the report of recording %s (owner %s)", admin.username, recording_id, report.owner)
    return report


@router.get("/recordings/{recording_id}/failures/{failure_id}/clip")
def get_clip(
    recording_id: str, failure_id: str, admin: models.User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    path = admin_service.clip_path(db, recording_id, failure_id)
    if path is None:
        raise not_found()
    log.info("admin %s viewed clip %s of recording %s", admin.username, failure_id, recording_id)
    return FileResponse(path, media_type="video/mp4")
