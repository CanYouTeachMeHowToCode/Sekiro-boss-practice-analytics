"""The same attempt and analytics code path must work for every boss in the seed data."""

import pytest

from app.seed import load_boss_data

BOSSES = load_boss_data()

# One (boss, phase, move) case per phase of every boss, using the phase's first move.
PHASE_CASES = [
    pytest.param(boss.id, phase.phase_number, phase.moves[0].id, id=f"{boss.id}-phase-{phase.phase_number}")
    for boss in BOSSES
    for phase in boss.phases
]


def _move_outside_phase(boss):
    """A (phase, move) pair where the move belongs to the boss but not to that phase, if one exists."""
    for phase in boss.phases:
        in_phase = {m.id for m in phase.moves}
        for other in boss.phases:
            for move in other.moves:
                if move.id not in in_phase:
                    return phase.phase_number, move.id
    return None


MISMATCH_CASES = [
    pytest.param(boss.id, *pair, id=boss.id) for boss in BOSSES if (pair := _move_outside_phase(boss)) is not None
]


def test_every_boss_in_the_seed_data_is_served(client):
    resp = client.get("/api/bosses")
    assert {b["id"] for b in resp.json()} == {b.id for b in BOSSES}

    for boss in BOSSES:
        detail = client.get(f"/api/bosses/{boss.id}").json()
        assert [p["phase_number"] for p in detail["phases"]] == [p.phase_number for p in boss.phases]
        for served, seeded in zip(detail["phases"], boss.phases):
            assert [m["id"] for m in served["moves"]] == [m.id for m in seeded.moves]


@pytest.mark.parametrize(("boss_id", "phase_number", "move_id"), PHASE_CASES)
def test_failed_attempt_can_be_recorded_in_every_phase(client, boss_id, phase_number, move_id):
    resp = client.post(
        f"/api/bosses/{boss_id}/attempts",
        json={"result": "failed", "phase_reached": phase_number, "failure_move_id": move_id},
    )
    assert resp.status_code == 201
    assert resp.json()["phase_reached"] == phase_number
    assert resp.json()["failure_move_id"] == move_id

    analytics = client.get(f"/api/bosses/{boss_id}/analytics").json()
    assert analytics["total_attempts"] == 1
    assert analytics["main_bottleneck_phase"] == phase_number
    assert analytics["most_common_failure_move"] == move_id


@pytest.mark.parametrize("boss", BOSSES, ids=[b.id for b in BOSSES])
def test_victory_is_recorded_at_each_bosss_own_final_phase(client, boss):
    resp = client.post(f"/api/bosses/{boss.id}/attempts", json={"result": "victory"})
    assert resp.status_code == 201
    assert resp.json()["phase_reached"] == max(p.phase_number for p in boss.phases)
    assert client.get(f"/api/bosses/{boss.id}/analytics").json()["defeated"] is True


@pytest.mark.parametrize(("boss_id", "phase_number", "move_id"), MISMATCH_CASES)
def test_move_from_a_different_phase_is_rejected(client, boss_id, phase_number, move_id):
    resp = client.post(
        f"/api/bosses/{boss_id}/attempts",
        json={"result": "failed", "phase_reached": phase_number, "failure_move_id": move_id},
    )
    assert resp.status_code == 400
    assert f"does not appear in phase {phase_number}" in resp.json()["detail"]
    assert client.get(f"/api/bosses/{boss_id}/attempts").json() == []


def test_phase_two_only_move_is_rejected_in_phase_one(client):
    resp = client.post(
        "/api/bosses/guardian-ape/attempts",
        json={"result": "failed", "phase_reached": 1, "failure_move_id": "blood-scream"},
    )
    assert resp.status_code == 400

    resp = client.post(
        "/api/bosses/guardian-ape/attempts",
        json={"result": "failed", "phase_reached": 2, "failure_move_id": "blood-scream"},
    )
    assert resp.status_code == 201


def test_move_from_another_boss_is_rejected(client):
    resp = client.post(
        "/api/bosses/genichiro-ashina/attempts",
        json={"result": "failed", "phase_reached": 1, "failure_move_id": "shadowfall"},
    )
    assert resp.status_code == 400
    assert "does not belong to boss" in resp.json()["detail"]


def test_attempts_and_analytics_stay_separate_per_boss(client):
    for move in ("perilous-sweep", "perilous-sweep", "shadowfall"):
        client.post(
            "/api/bosses/owl-father/attempts",
            json={"result": "failed", "phase_reached": 1, "failure_move_id": move},
        )
    client.post(
        "/api/bosses/genichiro-ashina/attempts",
        json={"result": "failed", "phase_reached": 2, "failure_move_id": "floating-passage"},
    )

    owl = client.get("/api/bosses/owl-father/analytics").json()
    genichiro = client.get("/api/bosses/genichiro-ashina/analytics").json()

    assert owl["total_attempts"] == 3
    assert owl["most_common_failure_move"] == "perilous-sweep"
    assert genichiro["total_attempts"] == 1
    assert genichiro["most_common_failure_move"] == "floating-passage"
    assert {a["boss_id"] for a in client.get("/api/bosses/owl-father/attempts").json()} == {"owl-father"}
    assert client.get("/api/bosses/lady-butterfly/analytics").json()["total_attempts"] == 0
