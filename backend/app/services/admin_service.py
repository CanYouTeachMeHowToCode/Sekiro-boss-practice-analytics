"""The read-only admin view of every user's recordings (owner decision, 2026-11-18).

A deliberate exception to per-user isolation (CLAUDE.md 7.3), for the private test: an admin may list every recording
and open any report and clip, but nothing here changes, deletes or reassigns anything. Who is an admin is checked by
the router (app.auth.get_admin_user); the reports are built by the same code as the owner's (recording_service).
"""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import models as db
from app.models.recording import AdminRecording, AdminRecordingReport
from app.services import recording_service

# statuses the worker has not finished with, listed first in the order the worker takes them
ACTIVE = ("uploaded", "checking", "queued", "processing")


def _to_admin(row: db.Recording) -> AdminRecording:
    return AdminRecording(
        **recording_service.to_schema(row).model_dump(), owner=row.user.username, error=row.error, fps=row.fps
    )


def list_recordings(session: Session) -> list[AdminRecording]:
    """Every recording: those still waiting or being analysed first, oldest first (the worker's order), then the
    rest, newest first."""
    rows = list(
        session.scalars(
            select(db.Recording).options(selectinload(db.Recording.boss), selectinload(db.Recording.user))
        )
    )
    active = sorted((r for r in rows if r.status in ACTIVE), key=lambda r: (r.created_at, r.id))
    finished = sorted((r for r in rows if r.status not in ACTIVE), key=lambda r: (r.created_at, r.id), reverse=True)
    return [_to_admin(r) for r in active + finished]


def _find(session: Session, recording_id: str) -> db.Recording | None:
    if not recording_id.isdigit():
        return None
    return session.scalar(
        recording_service.report_query()
        .options(selectinload(db.Recording.user))
        .where(db.Recording.id == int(recording_id))
    )


def get_report(session: Session, recording_id: str) -> AdminRecordingReport | None:
    """Any user's recording report, or None when there is no such recording."""
    row = _find(session, recording_id)
    if row is None:
        return None
    return AdminRecordingReport(**recording_service.build_report(row).model_dump(), owner=row.user.username)


def clip_path(session: Session, recording_id: str, failure_id: str) -> Path | None:
    """The clip of one failure of any user's recording, or None."""
    row = _find(session, recording_id)
    return recording_service.failure_clip(session, row, failure_id) if row else None
