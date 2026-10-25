"""Uploaded fight recordings and their failure reports (V4 Milestone 3).

Every function takes the current user's id and only ever reads or changes that user's recordings: another user's
recording behaves exactly like one that does not exist.

Videos are written under RECORDINGS_DIR (a Docker volume in Compose), one folder per user, and never into the
database. An upload is streamed to a `.part` file and renamed when complete, so a recording row only ever points at
a whole file. The worker checks each upload (format, length, that it is castle Genichiro) and processes it.
"""

import hashlib
import os
import shutil
import uuid
from collections import Counter
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import models as db
from app.models.recording import (
    FailureEvent,
    MoveCandidate,
    MoveFailureCount,
    Recording,
    RecordingFailure,
    RecordingReport,
    RecordingStatus,
)
from app.services import boss_service

# the boss the failure report supports in M3
BOSS_SLUG = "genichiro-ashina"
MAX_UPLOAD_BYTES = 2 * 1024**3          # owner decision, 2026-10-25 (with at most 10 minutes, checked by the worker)
VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov"}


class UploadError(ValueError):
    """An upload that cannot be accepted; `code` is what the frontend translates."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def recordings_dir() -> Path:
    return Path(os.environ.get("RECORDINGS_DIR", "data/recordings"))


def max_upload_bytes() -> int:
    return int(os.environ.get("MAX_UPLOAD_BYTES", MAX_UPLOAD_BYTES))


def _to_schema(row: db.Recording) -> Recording:
    return Recording(
        id=str(row.id),
        filename=row.original_filename,
        status=RecordingStatus(row.status),
        reject_code=row.reject_code,
        progress=row.progress,
        size_bytes=row.size_bytes,
        duration_s=row.duration_s,
        created_at=row.created_at,
        processed_at=row.processed_at,
    )


def _own(session: Session, user_id: int, recording_id: str) -> db.Recording | None:
    if not recording_id.isdigit():
        return None
    return session.scalar(
        select(db.Recording).where(db.Recording.id == int(recording_id), db.Recording.user_id == user_id)
    )


class Upload:
    """One upload being written to disk: `write` each chunk as it arrives, then `finish` to record it."""

    def __init__(self, user_id: int, filename: str, declared_size: int | None):
        name = Path(filename or "").name
        suffix = Path(name).suffix.lower()
        if suffix not in VIDEO_SUFFIXES:
            raise UploadError("unsupported_type", f"Only {', '.join(sorted(VIDEO_SUFFIXES))} files can be uploaded")
        if declared_size is not None and declared_size > max_upload_bytes():
            raise UploadError("too_large", "The recording is larger than the upload limit")
        self.user_id, self.filename = user_id, name
        self.relative = Path(str(user_id)) / f"{uuid.uuid4().hex}{suffix}"
        self.path = recordings_dir() / self.relative
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.part = self.path.with_name(self.path.name + ".part")
        self.file = open(self.part, "wb")
        self.size, self.hash = 0, hashlib.sha256()

    def write(self, chunk: bytes) -> None:
        self.size += len(chunk)
        if self.size > max_upload_bytes():
            self.abort()
            raise UploadError("too_large", "The recording is larger than the upload limit")
        self.hash.update(chunk)
        self.file.write(chunk)

    def abort(self) -> None:
        self.file.close()
        self.part.unlink(missing_ok=True)

    def finish(self, session: Session) -> Recording:
        self.file.close()
        if self.size == 0:
            self.part.unlink(missing_ok=True)
            raise UploadError("empty", "The upload was empty")
        os.replace(self.part, self.path)
        boss = boss_service.get_boss_row(session, BOSS_SLUG)
        row = db.Recording(
            user_id=self.user_id,
            boss=boss,
            original_filename=self.filename,
            storage_path=self.relative.as_posix(),
            size_bytes=self.size,
            sha256=self.hash.hexdigest(),
            status=RecordingStatus.UPLOADED.value,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _to_schema(row)


def list_recordings(session: Session, user_id: int) -> list[Recording]:
    rows = session.scalars(
        select(db.Recording)
        .where(db.Recording.user_id == user_id)
        .order_by(db.Recording.created_at.desc(), db.Recording.id.desc())
    )
    return [_to_schema(row) for row in rows]


def get_recording(session: Session, user_id: int, recording_id: str) -> Recording | None:
    row = _own(session, user_id, recording_id)
    return _to_schema(row) if row else None


def get_report(session: Session, user_id: int, recording_id: str) -> RecordingReport | None:
    if not recording_id.isdigit():
        return None
    row = session.scalar(
        select(db.Recording)
        .where(db.Recording.id == int(recording_id), db.Recording.user_id == user_id)
        .options(selectinload(db.Recording.failures).selectinload(db.RecordingFailure.move))
    )
    if row is None:
        return None
    failures = [
        RecordingFailure(
            id=str(f.id),
            time_s=f.time_s,
            type=f.type,
            phase=f.phase,
            sure=f.sure,
            move_id=f.move.slug if f.move else None,
            candidates=[MoveCandidate(move_id=c["move"], score=c["score"]) for c in f.candidates or []],
            events=[FailureEvent(type=e["type"], time_s=e["time_s"]) for e in f.events or []],
            has_clip=bool(f.clip_path),
        )
        for f in row.failures
    ]
    counts: dict[str, Counter] = {}
    for f in failures:
        if f.sure and f.move_id:
            counts.setdefault(f.move_id, Counter())[f.type.value] += 1
    by_move = [
        MoveFailureCount(
            move_id=move,
            damage=c["damage"],
            posture_break=c["posture_break"],
            death=c["death"],
            total=sum(c.values()),
        )
        for move, c in counts.items()
    ]
    by_move.sort(key=lambda m: (-m.total, m.move_id))
    return RecordingReport(
        recording=_to_schema(row),
        failures=failures,
        by_move=by_move,
        uncertain=sum(1 for f in failures if not f.sure),
    )


def clip_path(session: Session, user_id: int, recording_id: str, failure_id: str) -> Path | None:
    """The clip of one failure of the user's own recording, or None."""
    row = _own(session, user_id, recording_id)
    if row is None or not failure_id.isdigit():
        return None
    failure = session.scalar(
        select(db.RecordingFailure).where(
            db.RecordingFailure.id == int(failure_id), db.RecordingFailure.recording_id == row.id
        )
    )
    if failure is None or not failure.clip_path:
        return None
    path = recordings_dir() / failure.clip_path
    return path if path.is_file() else None


def delete_recording(session: Session, user_id: int, recording_id: str) -> bool:
    """Deletes the user's recording, its failures, the video and its clips. False if there is no such recording."""
    row = _own(session, user_id, recording_id)
    if row is None:
        return False
    video = recordings_dir() / row.storage_path
    session.delete(row)
    session.commit()
    video.unlink(missing_ok=True)
    shutil.rmtree(clips_dir(video), ignore_errors=True)
    return True


def clips_dir(video: Path) -> Path:
    """Where the worker puts a recording's clips: next to the video, in a folder named after it."""
    return video.with_name(video.stem + "_clips")
