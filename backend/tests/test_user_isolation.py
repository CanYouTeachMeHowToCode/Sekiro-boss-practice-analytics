"""Every attempt belongs to one user, and nobody sees anyone else's (V3 Milestones 2-3)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import models as db
from app.main import app
from app.services import analytics_service, attempt_service
from app.services.game_analytics_service import compute_sekiro_analytics
from scripts.claim_attempts import ClaimError, claim_attempts, count_ownerless

BOSS = "genichiro-ashina"


def record(client, **fields):
    body = {"result": "failed", "phase_reached": 1, "failure_move_id": None, "failure_category": None, **fields}
    resp = client.post(f"/api/bosses/{BOSS}/attempts", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture()
def other_client(anon_client):
    """A second logged-in user with its own cookie jar, sharing the test database."""
    other = TestClient(app)
    resp = other.post("/api/auth/register", json={"username": "other", "password": "correct-horse"})
    assert resp.status_code == 201, resp.text
    return other


def boss_row(session, slug=BOSS):
    return session.scalar(select(db.Boss).where(db.Boss.slug == slug))


def add_ownerless_attempt(session, **fields):
    attempt = db.Attempt(boss=boss_row(session), **{"result": "failed", "phase_reached": 1, **fields})
    session.add(attempt)
    session.flush()
    return attempt


# --- API level ---------------------------------------------------------------


def test_attempt_history_is_per_user(client, other_client):
    mine = [record(client), record(client, phase_reached=2)]
    theirs = record(other_client, phase_reached=2, failure_move_id="floating-passage")

    my_history = client.get(f"/api/bosses/{BOSS}/attempts").json()
    their_history = other_client.get(f"/api/bosses/{BOSS}/attempts").json()

    assert {a["id"] for a in my_history} == {a["id"] for a in mine}
    assert [a["id"] for a in their_history] == [theirs["id"]]


def test_boss_analytics_and_progression_are_per_user(client, other_client):
    record(client, phase_reached=1)
    record(client, phase_reached=1)
    record(other_client, phase_reached=2, failure_move_id="floating-passage")

    mine = client.get(f"/api/bosses/{BOSS}/analytics").json()
    theirs = other_client.get(f"/api/bosses/{BOSS}/analytics").json()

    assert mine["total_attempts"] == 2
    assert mine["failure_by_phase"] == {"1": 2}
    assert mine["failure_by_move"] == {}
    assert theirs["total_attempts"] == 1
    assert theirs["most_common_failure_move"] == "floating-passage"
    assert len(client.get(f"/api/bosses/{BOSS}/progression").json()) == 2
    assert len(other_client.get(f"/api/bosses/{BOSS}/progression").json()) == 1


def test_sekiro_dashboard_is_per_user(client, other_client):
    mine = record(client)
    record(other_client)
    record(other_client)
    other_client.post("/api/bosses/guardian-ape/attempts", json={"result": "victory"})

    my_dashboard = client.get("/api/sekiro/analytics").json()
    their_dashboard = other_client.get("/api/sekiro/analytics").json()

    assert my_dashboard["total_attempts"] == 1
    assert my_dashboard["bosses_attempted"] == 1
    assert my_dashboard["bosses_defeated"] == 0
    assert my_dashboard["attempts_in_recent_window"] == 1
    assert [a["attempt_id"] for a in my_dashboard["recent_attempts"]] == [mine["id"]]
    assert their_dashboard["total_attempts"] == 3
    assert their_dashboard["bosses_defeated"] == 1


def test_a_user_id_in_the_request_body_is_ignored(client, other_client, seeded_session):
    me = seeded_session.scalar(select(db.User).where(db.User.username == "tester"))

    created = record(other_client, user_id=me.id)

    assert client.get(f"/api/bosses/{BOSS}/attempts").json() == []
    assert seeded_session.get(db.Attempt, int(created["id"])).user.username == "other"


def test_ownerless_attempts_are_visible_to_nobody(client, seeded_session):
    add_ownerless_attempt(seeded_session)

    assert client.get(f"/api/bosses/{BOSS}/attempts").json() == []
    assert client.get(f"/api/bosses/{BOSS}/analytics").json()["total_attempts"] == 0
    assert client.get("/api/sekiro/analytics").json()["total_attempts"] == 0


# --- Service level -----------------------------------------------------------


def test_services_only_return_the_given_users_attempts(seeded_session, make_user):
    wolf, emma = make_user("wolf"), make_user("emma")
    boss = boss_row(seeded_session)
    seeded_session.add_all(
        [
            db.Attempt(boss=boss, user=wolf, result="failed", phase_reached=1),
            db.Attempt(boss=boss, user=emma, result="failed", phase_reached=3),
        ]
    )
    add_ownerless_attempt(seeded_session, phase_reached=2)

    assert [a.phase_reached for a in attempt_service.get_attempts(seeded_session, wolf.id, BOSS)] == [1]
    assert analytics_service.compute_analytics(seeded_session, emma.id, BOSS).best_phase == 3
    assert [p.phase_reached for p in analytics_service.compute_progression(seeded_session, wolf.id, BOSS)] == [1]


def test_first_victory_is_counted_within_each_users_own_history(seeded_session, make_user):
    wolf, emma = make_user("wolf"), make_user("emma")
    boss = boss_row(seeded_session)
    # Interleaved: emma's win must not shift wolf's attempt numbering, or vice versa.
    for user, result in [(wolf, "failed"), (emma, "victory"), (wolf, "failed"), (wolf, "victory")]:
        seeded_session.add(db.Attempt(boss=boss, user=user, result=result, phase_reached=3))
        seeded_session.flush()

    wolf_row = next(b for b in compute_sekiro_analytics(seeded_session, wolf.id).bosses if b.id == BOSS)
    emma_row = next(b for b in compute_sekiro_analytics(seeded_session, emma.id).bosses if b.id == BOSS)

    assert (wolf_row.attempts, wolf_row.attempts_until_first_victory) == (3, 3)
    assert (emma_row.attempts, emma_row.attempts_until_first_victory) == (1, 1)


# --- Claiming ownerless attempts ---------------------------------------------


def test_claim_assigns_only_ownerless_attempts(seeded_session, make_user):
    owner, other = make_user("owner"), make_user("other")
    old = [add_ownerless_attempt(seeded_session), add_ownerless_attempt(seeded_session, phase_reached=2)]
    theirs = db.Attempt(boss=boss_row(seeded_session), user=other, result="failed", phase_reached=1)
    seeded_session.add(theirs)
    seeded_session.flush()

    claimed = claim_attempts(seeded_session, "OWNER")

    assert claimed == 2
    assert all(a.user_id == owner.id for a in old)
    assert theirs.user_id == other.id
    assert count_ownerless(seeded_session) == 0
    assert claim_attempts(seeded_session, "owner") == 0


def test_claim_refuses_an_unknown_user(seeded_session):
    add_ownerless_attempt(seeded_session)

    with pytest.raises(ClaimError):
        claim_attempts(seeded_session, "nobody")

    assert count_ownerless(seeded_session) == 1
