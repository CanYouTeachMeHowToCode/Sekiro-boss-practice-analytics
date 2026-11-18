"""The read-only admin view (owner decision, 2026-11-18): an admin sees every user's recordings, reports and clips;
for everyone else the admin paths do not exist, and nothing about the owners' own view changes."""

import logging
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import models as db
from app.main import app
from scripts.set_admin import SetAdminError, set_admin

VIDEO = b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)) * 4
NOT_FOUND = {"detail": "Not Found"}


@pytest.fixture(autouse=True)
def recordings_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("RECORDINGS_DIR", str(tmp_path))
    return tmp_path


def register(username):
    """A new logged-in user with its own cookie jar, sharing the test database."""
    c = TestClient(app)
    resp = c.post("/api/auth/register", json={"username": username, "password": "correct-horse"})
    assert resp.status_code == 201, resp.text
    return c


@pytest.fixture()
def admin_client(anon_client, seeded_session):
    c = register("chief")
    set_admin(seeded_session, "chief")
    return c


@pytest.fixture()
def other_client(anon_client):
    return register("other")


def upload(client, filename="fight.mp4"):
    resp = client.post(f"/api/recordings?filename={filename}", content=VIDEO)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def add_failure_with_clip(session, recording_id, recordings_dir):
    rec = session.get(db.Recording, int(recording_id))
    move = session.scalar(select(db.Move).where(db.Move.boss_id == rec.boss_id, db.Move.slug == "floating-passage"))
    (recordings_dir / "clip.mp4").write_bytes(VIDEO)
    failure = db.RecordingFailure(
        recording=rec, time_s=12.5, type="damage", phase=1, sure=True, move=move,
        candidates=[{"move": "floating-passage", "score": 0.21}], events=[{"type": "damage", "time_s": 12.5}],
        clip_path="clip.mp4",
    )
    rec.status = "done"
    rec.progress = 1.0
    session.add(failure)
    session.flush()
    return failure


# --- who is an admin -----------------------------------------------------------


def test_me_says_whether_the_user_is_an_admin(client, seeded_session):
    assert client.get("/api/auth/me").json()["is_admin"] is False
    set_admin(seeded_session, "tester")
    assert client.get("/api/auth/me").json()["is_admin"] is True
    set_admin(seeded_session, "tester", admin=False)
    assert client.get("/api/auth/me").json()["is_admin"] is False


def test_no_api_makes_anyone_an_admin(anon_client):
    resp = anon_client.post(
        "/api/auth/register", json={"username": "sneaky", "password": "correct-horse", "is_admin": True}
    )
    assert resp.status_code == 201 and resp.json()["is_admin"] is False
    resp = anon_client.patch("/api/auth/me", json={"preferred_language": "en", "is_admin": True})
    assert resp.status_code == 200 and resp.json()["is_admin"] is False
    assert anon_client.get("/api/auth/me").json()["is_admin"] is False


def test_set_admin_needs_an_existing_user(seeded_session):
    with pytest.raises(SetAdminError):
        set_admin(seeded_session, "nobody")


# --- what an admin sees ------------------------------------------------------------


def test_admin_lists_every_users_recordings_waiting_ones_first(admin_client, client, other_client, seeded_session):
    old_done = upload(client, "old.mp4")
    queued = upload(other_client, "queued.mp4")
    processing = upload(client, "processing.mp4")
    new_rejected = upload(other_client, "rejected.mp4")
    start = datetime(2026, 11, 18, 6, 0, tzinfo=timezone.utc)
    settings = {
        old_done: ("done", 0),
        processing: ("processing", 1),
        queued: ("queued", 2),
        new_rejected: ("rejected", 3),
    }
    for rec_id, (status, minutes) in settings.items():
        row = seeded_session.get(db.Recording, int(rec_id))
        row.status = status
        row.created_at = start + timedelta(minutes=minutes)
        if status == "rejected":
            row.reject_code = "not_sekiro"
        if status == "processing":
            row.progress = 0.4
    seeded_session.flush()

    rows = admin_client.get("/api/admin/recordings").json()
    # waiting or being analysed first, in the worker's order (oldest first); then the rest, newest first
    assert [r["id"] for r in rows] == [processing, queued, new_rejected, old_done]
    by_id = {r["id"]: r for r in rows}
    assert by_id[queued]["owner"] == "other" and by_id[processing]["owner"] == "tester"
    assert by_id[processing]["progress"] == 0.4
    assert by_id[new_rejected]["reject_code"] == "not_sekiro"


def test_admin_opens_any_users_report_and_clip(admin_client, client, seeded_session, recordings_dir):
    rec_id = upload(client)
    failure = add_failure_with_clip(seeded_session, rec_id, recordings_dir)

    report = admin_client.get(f"/api/admin/recordings/{rec_id}")
    assert report.status_code == 200
    body = report.json()
    assert body["owner"] == "tester"
    assert body["recording"]["status"] == "done"
    # the same report the owner gets, plus whose it is
    own = client.get(f"/api/recordings/{rec_id}").json()
    assert {k: v for k, v in body.items() if k != "owner"} == own

    clip = admin_client.get(f"/api/admin/recordings/{rec_id}/failures/{failure.id}/clip")
    assert clip.status_code == 200 and clip.content == VIDEO
    part = admin_client.get(
        f"/api/admin/recordings/{rec_id}/failures/{failure.id}/clip", headers={"Range": "bytes=10-19"}
    )
    assert part.status_code == 206 and part.content == VIDEO[10:20]


@pytest.mark.parametrize("bad_id", ["abc", "999999"])
def test_unknown_recordings_are_not_found_for_the_admin(admin_client, bad_id):
    assert admin_client.get(f"/api/admin/recordings/{bad_id}").json() == NOT_FOUND
    assert admin_client.get(f"/api/admin/recordings/{bad_id}/failures/1/clip").json() == NOT_FOUND


def test_a_failure_of_another_recording_is_not_found_through_this_one(admin_client, client, seeded_session, recordings_dir):
    first = upload(client)
    second = upload(client)
    failure = add_failure_with_clip(seeded_session, second, recordings_dir)
    resp = admin_client.get(f"/api/admin/recordings/{first}/failures/{failure.id}/clip")
    assert resp.status_code == 404


def test_the_admin_view_changes_nothing(admin_client, client, seeded_session):
    rec_id = upload(client)
    # no admin endpoint deletes or changes
    for method in ("delete", "patch", "put", "post"):
        assert getattr(admin_client, method)(f"/api/admin/recordings/{rec_id}").status_code == 405
    # the owners' own API still treats another user's recording as missing, admin or not
    assert admin_client.delete(f"/api/recordings/{rec_id}").status_code == 404
    assert admin_client.get(f"/api/recordings/{rec_id}").status_code == 404
    assert admin_client.get("/api/recordings").json() == []
    assert client.get(f"/api/recordings/{rec_id}").status_code == 200


def test_admin_views_are_logged(admin_client, client, seeded_session, recordings_dir, caplog, monkeypatch):
    # The migration tests run Alembic in this process, and its logging setup disables the loggers that exist by then;
    # the server runs Alembic in a process of its own before starting the app.
    monkeypatch.setattr(logging.getLogger("app.admin"), "disabled", False)
    rec_id = upload(client)
    failure = add_failure_with_clip(seeded_session, rec_id, recordings_dir)
    with caplog.at_level(logging.INFO, logger="app.admin"):
        admin_client.get(f"/api/admin/recordings/{rec_id}")
        admin_client.get(f"/api/admin/recordings/{rec_id}/failures/{failure.id}/clip")
    lines = [r.getMessage() for r in caplog.records if r.name == "app.admin"]
    assert lines == [
        f"admin chief viewed the report of recording {rec_id} (owner tester)",
        f"admin chief viewed clip {failure.id} of recording {rec_id}",
    ]


# --- everyone else -----------------------------------------------------------------


def test_the_admin_view_does_not_exist_for_anyone_else(client, anon_client, seeded_session, recordings_dir):
    rec_id = upload(client)
    failure = add_failure_with_clip(seeded_session, rec_id, recordings_dir)
    logged_out = TestClient(app)
    paths = [
        "/api/admin/recordings",
        f"/api/admin/recordings/{rec_id}",
        f"/api/admin/recordings/{rec_id}/failures/{failure.id}/clip",
    ]
    # the same answer as a path that does not exist
    assert logged_out.get("/api/admin/no-such-path").json() == NOT_FOUND
    for who in (client, logged_out):
        for path in paths:
            resp = who.get(path)
            assert (resp.status_code, resp.json()) == (404, NOT_FOUND), (path, resp.text)


def test_an_admin_who_is_no_longer_one_loses_the_view(admin_client, seeded_session):
    assert admin_client.get("/api/admin/recordings").status_code == 200
    set_admin(seeded_session, "chief", admin=False)
    assert admin_client.get("/api/admin/recordings").json() == NOT_FOUND
