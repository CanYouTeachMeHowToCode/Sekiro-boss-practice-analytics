from datetime import datetime, timedelta, timezone

from sqlalchemy import event, select

from app.db import models as db
from app.seed import load_boss_data
from app.services.game_analytics_service import compute_sekiro_analytics

BOSS_IDS = [b.id for b in load_boss_data()]


def record(client, boss, **fields):
    resp = client.post(f"/api/bosses/{boss}/attempts", json=fields)
    assert resp.status_code == 201
    return resp.json()


def rows_by_id(data):
    return {row["id"]: row for row in data["bosses"]}


def test_no_attempts_yet(client):
    data = client.get("/api/sekiro/analytics").json()

    assert data["total_bosses"] == len(BOSS_IDS)
    assert (data["bosses_attempted"], data["bosses_defeated"], data["total_attempts"]) == (0, 0, 0)
    assert data["most_practiced_bosses"] == []
    assert data["bosses_requiring_most_attempts"] == []
    assert data["most_attempts_to_defeat"] is None
    assert data["recent_attempts"] == []
    assert [row["id"] for row in data["bosses"]] == BOSS_IDS
    assert all(row["attempts"] == 0 and not row["defeated"] for row in data["bosses"])


def test_summarizes_practice_across_bosses(client):
    for _ in range(3):
        record(client, "owl-father", result="failed", phase_reached=1, failure_move_id="perilous-sweep")
    record(client, "genichiro-ashina", result="failed", phase_reached=1, failure_move_id="perilous-thrust")
    record(client, "genichiro-ashina", result="failed", phase_reached=2)
    record(client, "genichiro-ashina", result="victory")
    record(client, "lady-butterfly", result="victory")
    record(client, "isshin-sword-saint", result="failed", phase_reached=2)

    data = client.get("/api/sekiro/analytics").json()

    assert data["bosses_attempted"] == 4
    assert data["bosses_defeated"] == 2
    assert data["total_attempts"] == 8
    # Owl and Genichiro both have 3 attempts, so both are reported.
    assert data["most_practiced_bosses"] == ["genichiro-ashina", "owl-father"]
    # Among defeated bosses, Genichiro took 3 attempts and Lady Butterfly 1.
    assert data["bosses_requiring_most_attempts"] == ["genichiro-ashina"]
    assert data["most_attempts_to_defeat"] == 3

    rows = rows_by_id(data)
    assert rows["genichiro-ashina"] | {"last_attempt_at": None} == {
        "id": "genichiro-ashina",
        "name": "Genichiro Ashina",
        "name_zh": "苇名弦一郎",
        "total_phases": 3,
        "attempts": 3,
        "best_phase": 3,
        "defeated": True,
        "attempts_until_first_victory": 3,
        "last_attempt_at": None,
    }
    assert rows["owl-father"]["defeated"] is False
    assert rows["owl-father"]["attempts_until_first_victory"] is None
    assert rows["owl-father"]["best_phase"] == 1
    assert rows["lady-butterfly"]["attempts_until_first_victory"] == 1
    assert rows["guardian-ape"]["attempts"] == 0
    assert rows["guardian-ape"]["last_attempt_at"] is None


def test_first_victory_ignores_later_victories(client):
    record(client, "lady-butterfly", result="failed", phase_reached=1)
    record(client, "lady-butterfly", result="victory")
    record(client, "lady-butterfly", result="victory")

    row = rows_by_id(client.get("/api/sekiro/analytics").json())["lady-butterfly"]
    assert row["attempts_until_first_victory"] == 2


def test_recent_attempts_are_newest_first_with_names_and_capped_at_ten(client):
    for phase in (1, 2) * 6:
        record(client, "owl-father", result="failed", phase_reached=phase)
    last = record(client, "guardian-ape", result="failed", phase_reached=2, failure_move_id="blood-scream")

    recent = client.get("/api/sekiro/analytics").json()["recent_attempts"]

    assert len(recent) == 10
    assert recent[0] | {"timestamp": None} == {
        "attempt_id": last["id"],
        "boss_id": "guardian-ape",
        "boss_name": "Guardian Ape",
        "boss_name_zh": "狮子猿",
        "timestamp": None,
        "result": "failed",
        "phase_reached": 2,
        "failure_move_id": "blood-scream",
        "failure_move_name": "Blood Scream",
        "failure_move_name_zh": "血之咆哮",
        "failure_category": None,
    }
    assert [int(a["attempt_id"]) for a in recent] == sorted((int(a["attempt_id"]) for a in recent), reverse=True)


def test_counts_only_attempts_from_the_last_seven_days(seeded_session, make_user):
    now = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)
    user = make_user("wolf")
    owl = seeded_session.scalar(select(db.Boss).where(db.Boss.slug == "owl-father"))
    for days_ago in (0, 3, 6.9, 7.1, 30):
        seeded_session.add(
            db.Attempt(
                boss=owl, user=user, result="failed", phase_reached=1, created_at=now - timedelta(days=days_ago)
            )
        )
    seeded_session.flush()

    data = compute_sekiro_analytics(seeded_session, user.id, now=now)

    assert data.recent_window_days == 7
    assert data.attempts_in_recent_window == 3
    assert data.total_attempts == 5


def test_uses_a_fixed_number_of_queries_regardless_of_boss_count(seeded_session, make_user):
    user = make_user("wolf")
    statements = []

    def listener(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    connection = seeded_session.connection()
    event.listen(connection, "before_cursor_execute", listener)
    try:
        compute_sekiro_analytics(seeded_session, user.id)
    finally:
        event.remove(connection, "before_cursor_execute", listener)

    # Per-boss stats, the 7-day count, and recent attempts - not one query per boss.
    assert len(statements) == 3
