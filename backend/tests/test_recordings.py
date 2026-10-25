"""Uploaded recordings and their failure reports (V4 Milestone 3): only their owner ever sees or changes them."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import models as db
from app.main import app
from app.services import recording_service

VIDEO = b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)) * 4


@pytest.fixture(autouse=True)
def recordings_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDINGS_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture()
def other_client(anon_client):
    """A second logged-in user with its own cookie jar, sharing the test database."""
    other = TestClient(app)
    resp = other.post("/api/auth/register", json={"username": "other", "password": "correct-horse"})
    assert resp.status_code == 201, resp.text
    return other


def upload(client, body=VIDEO, filename="fight.mp4"):
    return client.post(f"/api/recordings?filename={filename}", content=body)


def add_failures(session, recording_id, recordings_dir):
    """Failures as the worker would write them: two sure ones of one move, one sure of another, one uncertain."""
    rec = session.get(db.Recording, int(recording_id))
    boss = rec.boss
    move = {m.slug: m for m in session.scalars(select(db.Move).where(db.Move.boss_id == boss.id))}
    clip = recordings_dir / "clip.mp4"
    clip.write_bytes(VIDEO)
    rows = [
        db.RecordingFailure(recording=rec, time_s=12.5, type="damage", phase=1, sure=True, move=move["floating-passage"],
                            candidates=[{"move": "floating-passage", "score": 0.21}], events=[{"type": "damage", "time_s": 12.5}],
                            clip_path="clip.mp4"),
        db.RecordingFailure(recording=rec, time_s=40.0, type="death", phase=1, sure=True, move=move["floating-passage"],
                            candidates=[{"move": "floating-passage", "score": 0.25}],
                            events=[{"type": "damage", "time_s": 40.0}, {"type": "death", "time_s": 40.0}]),
        db.RecordingFailure(recording=rec, time_s=70.0, type="damage", phase=2, sure=True, move=move["hawk-shot"],
                            candidates=[{"move": "hawk-shot", "score": 0.3}], events=[{"type": "damage", "time_s": 70.0}]),
        db.RecordingFailure(recording=rec, time_s=95.0, type="posture_break", phase=2, sure=False,
                            candidates=[{"move": "counter-slash", "score": 0.12}, {"move": "deflect-counter-slash", "score": 0.11}],
                            events=[{"type": "posture_break", "time_s": 95.0}]),
    ]
    session.add_all(rows)
    session.flush()
    return rows


# --- upload ------------------------------------------------------------------


def test_upload_streams_the_video_to_disk_and_lists_it_only_for_its_owner(client, other_client, recordings_dir, seeded_session):
    resp = upload(client)
    assert resp.status_code == 201, resp.text
    rec = resp.json()
    assert rec["status"] == "uploaded" and rec["filename"] == "fight.mp4" and rec["size_bytes"] == len(VIDEO)

    row = seeded_session.get(db.Recording, int(rec["id"]))
    assert (recordings_dir / row.storage_path).read_bytes() == VIDEO
    assert row.boss.slug == "genichiro-ashina"
    assert not list(recordings_dir.rglob("*.part"))

    assert [r["id"] for r in client.get("/api/recordings").json()] == [rec["id"]]
    assert other_client.get("/api/recordings").json() == []


def test_upload_keeps_only_the_file_name_of_the_path_it_is_given(client, seeded_session, recordings_dir):
    resp = upload(client, filename="..%2F..%2Fsecret%2Ffight.mp4")
    assert resp.status_code == 201, resp.text
    row = seeded_session.get(db.Recording, int(resp.json()["id"]))
    assert row.original_filename == "fight.mp4"
    assert (recordings_dir / row.storage_path).resolve().is_relative_to(recordings_dir.resolve())


@pytest.mark.parametrize("filename", ["notes.txt", "fight", "clip.avi"])
def test_upload_refuses_files_that_are_not_a_supported_video(client, filename):
    resp = upload(client, filename=filename)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "unsupported_type"


def test_upload_refuses_a_file_over_the_limit_and_leaves_nothing_behind(client, monkeypatch, recordings_dir, seeded_session):
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "100")
    resp = upload(client)
    assert resp.status_code == 413
    assert resp.json()["detail"]["code"] == "too_large"
    assert not [p for p in recordings_dir.rglob("*") if p.is_file()]
    assert seeded_session.scalar(select(db.Recording)) is None


def test_upload_refuses_an_empty_file(client, recordings_dir):
    resp = upload(client, body=b"")
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "empty"
    assert not [p for p in recordings_dir.rglob("*") if p.is_file()]


def test_recordings_need_a_login(anon_client):
    assert upload(anon_client).status_code == 401
    assert anon_client.get("/api/recordings").status_code == 401
    assert anon_client.get("/api/recordings/1").status_code == 401


# --- report ------------------------------------------------------------------


def test_report_counts_failures_per_move_from_sure_answers_only(client, seeded_session, recordings_dir):
    rec_id = upload(client).json()["id"]
    add_failures(seeded_session, rec_id, recordings_dir)

    report = client.get(f"/api/recordings/{rec_id}").json()
    assert [f["time_s"] for f in report["failures"]] == [12.5, 40.0, 70.0, 95.0]
    assert report["by_move"] == [
        {"move_id": "floating-passage", "damage": 1, "posture_break": 0, "death": 1, "total": 2},
        {"move_id": "hawk-shot", "damage": 1, "posture_break": 0, "death": 0, "total": 1},
    ]
    assert report["uncertain"] == 1
    unsure = report["failures"][3]
    assert unsure["sure"] is False and unsure["move_id"] is None
    assert [c["move_id"] for c in unsure["candidates"]] == ["counter-slash", "deflect-counter-slash"]
    assert [f["has_clip"] for f in report["failures"]] == [True, False, False, False]


def test_clip_is_served_to_its_owner_with_range_requests(client, seeded_session, recordings_dir):
    rec_id = upload(client).json()["id"]
    failure = add_failures(seeded_session, rec_id, recordings_dir)[0]

    whole = client.get(f"/api/recordings/{rec_id}/failures/{failure.id}/clip")
    assert whole.status_code == 200 and whole.content == VIDEO
    part = client.get(f"/api/recordings/{rec_id}/failures/{failure.id}/clip", headers={"Range": "bytes=10-19"})
    assert part.status_code == 206 and part.content == VIDEO[10:20]


def test_a_failure_without_a_clip_has_no_clip(client, seeded_session, recordings_dir):
    rec_id = upload(client).json()["id"]
    failure = add_failures(seeded_session, rec_id, recordings_dir)[1]
    assert client.get(f"/api/recordings/{rec_id}/failures/{failure.id}/clip").status_code == 404


def test_another_users_recording_does_not_exist_for_you(client, other_client, seeded_session, recordings_dir):
    rec_id = upload(client).json()["id"]
    failure = add_failures(seeded_session, rec_id, recordings_dir)[0]

    assert other_client.get(f"/api/recordings/{rec_id}").status_code == 404
    assert other_client.get(f"/api/recordings/{rec_id}/failures/{failure.id}/clip").status_code == 404
    assert other_client.delete(f"/api/recordings/{rec_id}").status_code == 404
    assert client.get(f"/api/recordings/{rec_id}").status_code == 200


def test_a_failure_of_another_recording_is_not_found_through_yours(client, seeded_session, recordings_dir):
    mine = upload(client).json()["id"]
    second = upload(client).json()["id"]
    failure = add_failures(seeded_session, second, recordings_dir)[0]
    assert client.get(f"/api/recordings/{mine}/failures/{failure.id}/clip").status_code == 404


@pytest.mark.parametrize("bad_id", ["abc", "999999"])
def test_unknown_recording_ids_are_not_found(client, bad_id):
    assert client.get(f"/api/recordings/{bad_id}").status_code == 404


# --- delete ------------------------------------------------------------------


def test_delete_removes_the_recording_its_failures_video_and_clips(client, seeded_session, recordings_dir):
    rec_id = upload(client).json()["id"]
    add_failures(seeded_session, rec_id, recordings_dir)
    row = seeded_session.get(db.Recording, int(rec_id))
    video = recordings_dir / row.storage_path
    clips = recording_service.clips_dir(video)
    clips.mkdir()
    (clips / "1.mp4").write_bytes(VIDEO)

    assert client.delete(f"/api/recordings/{rec_id}").status_code == 204
    assert client.get(f"/api/recordings/{rec_id}").status_code == 404
    assert not video.exists() and not clips.exists()
    seeded_session.expire_all()
    assert seeded_session.scalar(select(db.RecordingFailure)) is None


# --- database constraints ----------------------------------------------------


def recording_row(session, make_user, **fields):
    user = make_user("wolf")
    boss = session.scalar(select(db.Boss).where(db.Boss.slug == "genichiro-ashina"))
    row = db.Recording(user=user, boss=boss, original_filename="f.mp4", storage_path="1/f.mp4", size_bytes=1,
                       sha256="0" * 64, **fields)
    session.add(row)
    return row


@pytest.mark.parametrize("fields", [{"status": "finished"}, {"progress": 1.5}, {"status": "done", "reject_code": "too_long"}])
def test_recording_check_constraints(seeded_session, make_user, fields):
    recording_row(seeded_session, make_user, **fields)
    with pytest.raises(IntegrityError):
        seeded_session.flush()


def test_a_failure_names_a_move_only_when_the_system_is_sure(seeded_session, make_user):
    rec = recording_row(seeded_session, make_user)
    move = seeded_session.scalar(select(db.Move).where(db.Move.slug == "floating-passage"))
    seeded_session.add(db.RecordingFailure(recording=rec, time_s=1.0, type="damage", phase=1, sure=False, move=move,
                                           candidates=[], events=[]))
    with pytest.raises(IntegrityError):
        seeded_session.flush()


def test_a_failure_type_is_one_of_the_three(seeded_session, make_user):
    rec = recording_row(seeded_session, make_user)
    seeded_session.add(db.RecordingFailure(recording=rec, time_s=1.0, type="resurrection", phase=1, sure=False,
                                           candidates=[], events=[]))
    with pytest.raises(IntegrityError):
        seeded_session.flush()
