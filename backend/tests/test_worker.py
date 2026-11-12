"""The recording worker (V4 Milestone 3): format checks, the recording lifecycle and the failure clips.

Tests that read or cut real videos need ffmpeg and ffprobe; they are skipped without them, unless
REQUIRE_MEDIA_TESTS is set (CI installs ffmpeg and sets it).
"""

import os
import shutil
import subprocess

import pytest
from sqlalchemy import select

from app.db import models as db
from app.worker import checks, jobs, media
from app.worker.analyzer import FoundFailure
from app.worker.media import VideoInfo

# --- format rules -------------------------------------------------------------


@pytest.mark.parametrize(
    "info, code",
    [
        (VideoInfo(2560, 1440, 60.0, 300.0), None),
        (VideoInfo(1920, 1080, 59.94, 600.0), None),
        (VideoInfo(1280, 720, 29.97, 30.0), None),
        (VideoInfo(3840, 2160, 60.0, 30.0), None),
        (VideoInfo(2560, 1440, 60.0, 600.5), "too_long"),
        (VideoInfo(3440, 1440, 60.0, 300.0), "not_16_9"),
        (VideoInfo(1440, 1080, 60.0, 300.0), "not_16_9"),
        (VideoInfo(1024, 576, 60.0, 300.0), "unsupported_resolution"),
        (VideoInfo(7680, 4320, 60.0, 300.0), "unsupported_resolution"),
        (VideoInfo(2560, 1440, 144.0, 300.0), "unsupported_frame_rate"),
        (VideoInfo(2560, 1440, 24.0, 300.0), "unsupported_frame_rate"),
        (VideoInfo(2560, 1440, 60.0, 0.0), "unreadable"),
    ],
)
def test_format_rules(info, code):
    assert checks.format_problem(info) == code


# --- media --------------------------------------------------------------------


@pytest.fixture(scope="session")
def ffmpeg():
    if media.ffmpeg_available():
        return
    if os.environ.get("REQUIRE_MEDIA_TESTS"):
        pytest.fail("REQUIRE_MEDIA_TESTS is set but ffmpeg or ffprobe is not installed")
    pytest.skip("ffmpeg and ffprobe are not installed")


def make_video(path, width=1280, height=720, fps=60, seconds=6):
    """A test pattern with a tone, encoded as H.264 and AAC."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={width}x{height}:rate={fps}",
         "-f", "lavfi", "-i", "sine=frequency=440", "-t", str(seconds), "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(path)],
        check=True,
    )
    return path


def test_probe_reads_the_size_frame_rate_and_length(ffmpeg, tmp_path):
    info = media.probe(make_video(tmp_path / "fight.mp4", 1920, 1080, 60, 2))
    assert (info.width, info.height) == (1920, 1080)
    assert info.fps == pytest.approx(60.0)
    assert info.duration_s == pytest.approx(2.0, abs=0.1)


def test_probe_refuses_a_file_that_is_not_a_video(ffmpeg, tmp_path):
    junk = tmp_path / "fight.mp4"
    junk.write_bytes(b"not a video at all")
    with pytest.raises(media.MediaError):
        media.probe(junk)


def test_a_clip_is_720p_h264_and_as_long_as_asked(ffmpeg, tmp_path):
    source = make_video(tmp_path / "fight.mp4", 1920, 1080, 60, 6)
    clip = tmp_path / "clips" / "1.mp4"
    media.cut_clip(source, 1.0, 4.0, clip)
    info = media.probe(clip)
    assert (info.width, info.height) == (1280, 720)
    assert info.duration_s == pytest.approx(3.0, abs=0.2)
    codec = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name",
                            "-of", "csv=p=0", str(clip)], capture_output=True, text=True, check=True).stdout.strip()
    assert codec == "h264"


# --- lifecycle ----------------------------------------------------------------


@pytest.fixture()
def recordings_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDINGS_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture()
def user(make_user):
    return make_user("wolf")


def add_recording(session, user, recordings_dir, name="fight.mp4", status="uploaded", video=None):
    """A recording row as the upload leaves it, with its file; the setup is committed, as the worker's steps commit."""
    path = recordings_dir / str(user.id) / name
    if video is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"not a video at all")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(video, path)
    boss = session.scalar(select(db.Boss).where(db.Boss.slug == "genichiro-ashina"))
    row = db.Recording(user=user, boss=boss, original_filename=name, storage_path=f"{user.id}/{name}",
                       size_bytes=path.stat().st_size, sha256="0" * 64, status=status)
    session.add(row)
    session.commit()
    return row


class FakeAnalyzer:
    """Stands in for the pipeline: reports the failures it is given, or raises."""

    version = "test-1"

    def __init__(self, failures=(), error=None, progress_seen=None):
        self.failures, self.error, self.progress_seen = list(failures), error, progress_seen

    def analyze(self, video, progress):
        assert video.is_file()
        progress(0.5)
        if self.progress_seen is not None:
            self.progress_seen.append(video)
        if self.error:
            raise self.error
        return self.failures


TWO_FAILURES = [
    FoundFailure(time_s=1.5, type="damage", phase=1, sure=True, move="floating-passage",
                 candidates=(("floating-passage", 0.21),), events=(("damage", 1.5),)),
    FoundFailure(time_s=4.0, type="death", phase=1, sure=False,
                 candidates=(("counter-slash", 0.12), ("deflect-counter-slash", 0.11)),
                 events=(("damage", 4.0), ("death", 4.0))),
]


def test_check_queues_a_supported_recording_and_saves_its_format(ffmpeg, seeded_session, user, recordings_dir, tmp_path):
    row = add_recording(seeded_session, user, recordings_dir, video=make_video(tmp_path / "src.mp4", 1280, 720, 60, 2))

    assert jobs.check_next(seeded_session).id == row.id
    seeded_session.refresh(row)
    assert row.status == "queued" and row.reject_code is None
    assert (row.width, row.height) == (1280, 720)
    assert row.fps == pytest.approx(60.0) and row.duration_s == pytest.approx(2.0, abs=0.1)


def test_check_rejects_an_unsupported_format_with_the_reason(ffmpeg, seeded_session, user, recordings_dir, tmp_path):
    row = add_recording(seeded_session, user, recordings_dir, video=make_video(tmp_path / "src.mp4", 960, 720, 30, 1))
    jobs.check_next(seeded_session)
    seeded_session.refresh(row)
    assert (row.status, row.reject_code) == ("rejected", "not_16_9")


def test_check_rejects_a_file_that_is_not_a_video(ffmpeg, seeded_session, user, recordings_dir):
    row = add_recording(seeded_session, user, recordings_dir)
    jobs.check_next(seeded_session)
    seeded_session.refresh(row)
    assert (row.status, row.reject_code) == ("rejected", "unreadable")


def test_processing_saves_the_failures_and_a_clip_of_each(ffmpeg, seeded_session, user, recordings_dir, tmp_path):
    row = add_recording(seeded_session, user, recordings_dir, video=make_video(tmp_path / "src.mp4", 1920, 1080, 60, 6))
    jobs.check_next(seeded_session)

    assert jobs.process_next(seeded_session, FakeAnalyzer(TWO_FAILURES)).id == row.id
    seeded_session.refresh(row)
    assert (row.status, row.progress, row.pipeline_version) == ("done", 1.0, "test-1")
    assert row.processed_at is not None and row.error is None
    sure, unsure = row.failures
    assert (sure.time_s, sure.type, sure.sure, sure.move.slug) == (1.5, "damage", True, "floating-passage")
    assert (unsure.sure, unsure.move, [c["move"] for c in unsure.candidates]) == (False, None, ["counter-slash", "deflect-counter-slash"])
    assert unsure.events == [{"type": "damage", "time_s": 4.0}, {"type": "death", "time_s": 4.0}]
    for failure in row.failures:
        clip = media.probe(recordings_dir / failure.clip_path)
        assert clip.height == 720
    # 3 s before to 2 s after, inside the 6-second video: 0-3.5 s and 1-6 s
    assert media.probe(recordings_dir / sure.clip_path).duration_s == pytest.approx(3.5, abs=0.2)
    assert media.probe(recordings_dir / unsure.clip_path).duration_s == pytest.approx(5.0, abs=0.2)


def test_progress_is_saved_while_the_analysis_runs(seeded_session, user, recordings_dir):
    row = add_recording(seeded_session, user, recordings_dir, status="queued")
    seen = []

    class Watching(FakeAnalyzer):
        def analyze(self, video, progress):
            progress(0.5)
            seen.append(seeded_session.scalar(select(db.Recording.progress).where(db.Recording.id == row.id)))
            return []

    jobs.process_next(seeded_session, Watching())
    assert seen == [0.5]
    seeded_session.refresh(row)
    assert (row.status, row.progress) == ("done", 1.0)


def test_a_failed_analysis_marks_the_recording_failed_and_keeps_nothing(seeded_session, user, recordings_dir):
    row = add_recording(seeded_session, user, recordings_dir, status="queued")
    jobs.process_next(seeded_session, FakeAnalyzer(error=RuntimeError("the pipeline broke")))
    seeded_session.refresh(row)
    assert row.status == "failed"
    assert row.error == "RuntimeError: the pipeline broke"
    assert row.failures == []


def test_a_move_the_boss_does_not_have_fails_the_recording(seeded_session, user, recordings_dir):
    row = add_recording(seeded_session, user, recordings_dir, status="queued")
    unknown = FoundFailure(time_s=1.0, type="damage", phase=1, sure=True, move="no-such-move")
    jobs.process_next(seeded_session, FakeAnalyzer([unknown]))
    seeded_session.refresh(row)
    assert row.status == "failed" and "no-such-move" in row.error
    assert row.failures == []


def test_without_a_pipeline_queued_recordings_wait(seeded_session, user, recordings_dir):
    row = add_recording(seeded_session, user, recordings_dir, status="queued")
    assert jobs.run_once(seeded_session, None) is False
    seeded_session.refresh(row)
    assert row.status == "queued"


def test_the_oldest_recording_is_taken_first(seeded_session, user, recordings_dir):
    first = add_recording(seeded_session, user, recordings_dir, name="first.mp4", status="queued")
    add_recording(seeded_session, user, recordings_dir, name="second.mp4", status="queued")
    assert jobs.claim(seeded_session, "queued", "processing").id == first.id


def test_recovery_puts_back_recordings_left_half_done(seeded_session, user, recordings_dir):
    checking = add_recording(seeded_session, user, recordings_dir, name="a.mp4", status="checking")
    processing = add_recording(seeded_session, user, recordings_dir, name="b.mp4", status="processing")
    processing.progress = 0.4
    processing.failures.append(db.RecordingFailure(time_s=1.0, type="damage", phase=1, sure=False, candidates=[], events=[]))
    seeded_session.commit()

    assert jobs.recover_interrupted(seeded_session) == 2
    seeded_session.refresh(checking)
    seeded_session.refresh(processing)
    assert checking.status == "uploaded"
    assert (processing.status, processing.progress, processing.failures) == ("queued", 0.0, [])
