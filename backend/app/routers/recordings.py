from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import models
from app.db.session import get_db
from app.models.recording import Recording, RecordingReport
from app.services import recording_service

# Every endpoint requires login and only ever covers the current user's recordings; another user's recording is a 404.
router = APIRouter(prefix="/api/recordings", tags=["recordings"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Recording not found")


@router.post("", response_model=Recording, status_code=status.HTTP_201_CREATED)
async def upload_recording(
    request: Request,
    filename: str = Query(..., description="The video's file name; its extension says the format."),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The request body is the video file itself, streamed to disk as it arrives (no multipart form), so a
    recording up to the 2 GB limit never has to fit in memory or a temporary file."""
    declared = request.headers.get("content-length")
    try:
        upload = recording_service.Upload(user.id, filename, int(declared) if declared and declared.isdigit() else None)
        try:
            async for chunk in request.stream():
                upload.write(chunk)
        except recording_service.UploadError:
            raise
        except Exception:
            upload.abort()
            raise
        return upload.finish(db)
    except recording_service.UploadError as exc:
        code = 413 if exc.code == "too_large" else 400
        raise HTTPException(status_code=code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.get("", response_model=list[Recording])
def list_recordings(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return recording_service.list_recordings(db, user.id)


@router.get("/{recording_id}", response_model=RecordingReport)
def get_report(recording_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = recording_service.get_report(db, user.id, recording_id)
    if report is None:
        raise _not_found()
    return report


@router.get("/{recording_id}/failures/{failure_id}/clip")
def get_clip(
    recording_id: str, failure_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """The failure's short H.264 clip; Range requests are supported, so the browser can seek."""
    path = recording_service.clip_path(db, user.id, recording_id, failure_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Clip not found")
    return FileResponse(path, media_type="video/mp4")


@router.delete("/{recording_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recording(recording_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not recording_service.delete_recording(db, user.id, recording_id):
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
