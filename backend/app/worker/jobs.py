"""The worker's steps on recordings in PostgreSQL.

    uploaded -> checking -> rejected (reject_code says why)
                         -> queued -> processing -> done
                                                -> failed (error says why)

A step claims the oldest recording in a status with SELECT ... FOR UPDATE SKIP LOCKED and moves it on in the same
transaction, so two workers never take the same recording. M3 runs one worker: when it starts, it puts back what it
was doing when it last stopped (recover_interrupted).
"""

import logging
import shutil
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models as db
from app.services.recording_service import clips_dir, recordings_dir
from app.worker import checks, media
from app.worker.analyzer import Analyzer

log = logging.getLogger(__name__)

CLIP_BEFORE_S, CLIP_AFTER_S = 3.0, 2.0
PROGRESS_STEP = 0.01          # save the progress at most once per percent


def claim(session: Session, from_status: str, to_status: str) -> db.Recording | None:
    row = session.scalar(
        select(db.Recording)
        .where(db.Recording.status == from_status)
        .order_by(db.Recording.created_at, db.Recording.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if row is None:
        return None
    row.status = to_status
    session.commit()
    return row


def recover_interrupted(session: Session) -> int:
    """Puts back the recordings a stopped worker left half done: checking goes back to uploaded, processing back to
    queued with its partial results removed. Returns how many."""
    rows = list(session.scalars(select(db.Recording).where(db.Recording.status.in_(("checking", "processing")))))
    for row in rows:
        if row.status == "processing":
            row.failures.clear()
            row.progress = 0.0
            row.status = "queued"
            shutil.rmtree(clips_dir(recordings_dir() / row.storage_path), ignore_errors=True)
        else:
            row.status = "uploaded"
    session.commit()
    return len(rows)


def check_next(session: Session) -> db.Recording | None:
    """Checks the oldest uploaded recording: rejected with a reason, or queued for processing."""
    row = claim(session, "uploaded", "checking")
    if row is None:
        return None
    try:
        info = media.probe(recordings_dir() / row.storage_path)
    except media.MediaError as exc:
        log.info("recording %s is unreadable: %s", row.id, exc)
        return _reject(session, row, "unreadable")
    row.width, row.height, row.fps, row.duration_s = info.width, info.height, info.fps, info.duration_s
    problem = checks.format_problem(info)
    if problem:
        return _reject(session, row, problem)
    row.status = "queued"
    session.commit()
    log.info("recording %s queued (%dx%d, %.2f fps, %.0f s)", row.id, info.width, info.height, info.fps, info.duration_s)
    return row


def _reject(session: Session, row: db.Recording, code: str) -> db.Recording:
    row.status, row.reject_code = "rejected", code
    session.commit()
    log.info("recording %s rejected: %s", row.id, code)
    return row


def _progress_saver(session: Session, row: db.Recording) -> Callable[[float], None]:
    def save(fraction: float) -> None:
        fraction = min(max(fraction, 0.0), 0.99)       # 1 only once the results are saved
        if fraction - row.progress >= PROGRESS_STEP:
            row.progress = fraction
            session.commit()
    return save


def process_next(session: Session, analyzer: Analyzer) -> db.Recording | None:
    """Analyses the oldest queued recording, saves its failures and cuts a clip of each: done, or failed with the
    error, keeping none of its partial results."""
    row = claim(session, "queued", "processing")
    if row is None:
        return None
    recording_id, video = row.id, recordings_dir() / row.storage_path
    try:
        found = analyzer.analyze(video, _progress_saver(session, row))
        moves = {m.slug: m for m in session.scalars(select(db.Move).where(db.Move.boss_id == row.boss_id))}
        for f in found:
            move = moves.get(f.move) if f.sure and f.move else None
            if f.sure and move is None:
                raise ValueError(f"the analysis named a move this boss does not have: {f.move!r}")
            row.failures.append(db.RecordingFailure(
                time_s=f.time_s, type=f.type, phase=f.phase, sure=f.sure, move=move,
                candidates=[{"move": slug, "score": score} for slug, score in f.candidates],
                events=[{"type": kind, "time_s": t} for kind, t in f.events],
            ))
        session.flush()
        end_of_video = row.duration_s if row.duration_s else float("inf")
        for failure in row.failures:
            clip = clips_dir(video) / f"{failure.id}.mp4"
            media.cut_clip(video, failure.time_s - CLIP_BEFORE_S, min(end_of_video, failure.time_s + CLIP_AFTER_S), clip)
            failure.clip_path = clip.relative_to(recordings_dir()).as_posix()
        row.status, row.progress, row.pipeline_version = "done", 1.0, analyzer.version
        row.processed_at = datetime.now(timezone.utc)
        session.commit()
        log.info("recording %s done: %d failures", recording_id, len(row.failures))
    except Exception as exc:  # noqa: BLE001 - any error fails this recording, not the worker
        session.rollback()
        shutil.rmtree(clips_dir(video), ignore_errors=True)
        row = session.get(db.Recording, recording_id)
        row.status, row.error = "failed", f"{type(exc).__name__}: {exc}"[:2000]
        session.commit()
        log.exception("recording %s failed", recording_id)
    return row


def run_once(session: Session, analyzer: Analyzer | None) -> bool:
    """One step of work: check an upload, else process a queued recording if a pipeline is installed. False when
    there was nothing to do."""
    if check_next(session) is not None:
        return True
    return analyzer is not None and process_next(session, analyzer) is not None
