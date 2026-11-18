"""scripts/reanalyze.py: a recording goes back to the worker's queue, keeping its video and nothing else."""

import pytest
from sqlalchemy import select

from app.db import models as db
from scripts.reanalyze import ReanalyzeError, reanalyze


@pytest.fixture()
def recordings_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDINGS_DIR", str(tmp_path))
    return tmp_path


def analysed_recording(session, make_user, recordings_dir, status="done"):
    user = make_user("wolf")
    video = recordings_dir / str(user.id) / "fight.mp4"
    clips = recordings_dir / str(user.id) / "fight_clips"
    clips.mkdir(parents=True)
    video.write_bytes(b"the video")
    (clips / "1.mp4").write_bytes(b"a clip")
    boss = session.scalar(select(db.Boss).where(db.Boss.slug == "genichiro-ashina"))
    row = db.Recording(user=user, boss=boss, original_filename="fight.mp4", storage_path=f"{user.id}/fight.mp4",
                       size_bytes=9, sha256="0" * 64, status=status, progress=1.0 if status == "done" else 0.4,
                       width=2560, height=1440, fps=30.0, duration_s=241.0, pipeline_version="v2")
    if status == "rejected":
        row.reject_code, row.progress = "not_sekiro", 0.0
    session.add(row)
    session.flush()
    session.add(db.RecordingFailure(recording=row, time_s=2.0, type="damage", phase=1, sure=False,
                                    candidates=[{"move": "floating-passage", "score": -1.0}],
                                    events=[{"type": "damage", "time_s": 2.0}], clip_path=f"{user.id}/fight_clips/1.mp4"))
    session.flush()
    return row, video, clips


@pytest.mark.parametrize("status", ["done", "failed", "rejected"])
def test_reanalyze_sends_a_finished_recording_back_keeping_only_its_video(seeded_session, make_user, recordings_dir, status):
    row, video, clips = analysed_recording(seeded_session, make_user, recordings_dir, status)

    reanalyze(seeded_session, row.id)

    seeded_session.refresh(row)
    assert (row.status, row.progress, row.reject_code, row.error, row.processed_at, row.pipeline_version) == (
        "uploaded", 0.0, None, None, None, None)
    assert row.failures == []
    assert video.read_bytes() == b"the video"
    assert not clips.exists()


@pytest.mark.parametrize("status", ["checking", "processing"])
def test_reanalyze_leaves_a_recording_the_worker_is_on(seeded_session, make_user, recordings_dir, status):
    row, video, clips = analysed_recording(seeded_session, make_user, recordings_dir, status)
    with pytest.raises(ReanalyzeError, match=status):
        reanalyze(seeded_session, row.id)
    assert row.status == status and clips.exists() and len(row.failures) == 1


def test_reanalyze_needs_an_existing_recording(seeded_session):
    with pytest.raises(ReanalyzeError):
        reanalyze(seeded_session, 999999)
