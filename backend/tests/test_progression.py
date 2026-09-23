from datetime import datetime, timedelta, timezone

import pytest

from app.models.attempt import Attempt, AttemptResult
from app.services.analytics_service import progression, summarize

START = datetime(2026, 9, 1, tzinfo=timezone.utc)


def history(*entries):
    """Attempts from oldest to newest, returned newest first like attempt_service does.

    Each entry is (phase_reached, failure_move_id), or "victory" at the given phase.
    """
    attempts = []
    for n, entry in enumerate(entries, start=1):
        if entry[0] == "victory":
            result, phase, move = AttemptResult.VICTORY, entry[1], None
        else:
            result, (phase, move) = AttemptResult.FAILED, entry
        attempts.append(
            Attempt(
                id=str(n),
                boss_id="genichiro-ashina",
                timestamp=START + timedelta(minutes=n),
                result=result,
                phase_reached=phase,
                failure_move_id=move,
            )
        )
    return list(reversed(attempts))


# ---- Controlled histories (no database) ----


def test_recent_window_shows_a_shifting_bottleneck():
    # Stuck in phase 1 for a long time, then mostly failing in phase 2 recently.
    attempts = history(
        *[(1, "perilous-thrust")] * 8,
        *[(2, "floating-passage")] * 4,
        (1, "perilous-thrust"),
    )

    stats = summarize(attempts, recent_window=5)

    assert stats.main_bottleneck_phase == 1
    assert stats.failure_by_phase == {"1": 9, "2": 4}
    assert stats.recent.main_bottleneck_phase == 2
    assert stats.recent.failure_by_phase == {"2": 4, "1": 1}
    assert stats.recent.most_common_failure_move == "floating-passage"


def test_recent_window_covers_only_the_available_attempts():
    stats = summarize(history((1, "perilous-thrust"), (2, "floating-passage")), recent_window=10)

    assert stats.recent.window_size == 10
    assert stats.recent.total_attempts == 2
    assert stats.recent.failure_by_phase == stats.failure_by_phase


def test_recent_window_counts_victories_but_not_as_failures():
    stats = summarize(history((1, "perilous-thrust"), ("victory", 3), (2, "floating-passage")), recent_window=2)

    assert stats.recent.total_attempts == 2
    assert stats.recent.failure_by_phase == {"2": 1}


@pytest.mark.parametrize(
    ("entries", "expected"),
    [
        ([(1, None), (2, None), ("victory", 3)], 3),
        ([("victory", 3)], 1),
        ([(1, None), ("victory", 3), (2, None), ("victory", 3)], 2),
        ([(1, None), (2, None)], None),
        ([], None),
    ],
    ids=["third-attempt", "first-attempt", "first-of-several-victories", "never-defeated", "no-attempts"],
)
def test_attempts_until_first_victory_includes_the_winning_attempt(entries, expected):
    stats = summarize(history(*entries))

    assert stats.attempts_until_first_victory == expected
    assert stats.defeated is (expected is not None)


def test_no_attempts_produces_empty_statistics():
    stats = summarize([], recent_window=10)

    assert stats.total_attempts == 0
    assert stats.best_phase is None
    assert stats.recent.total_attempts == 0
    assert stats.recent.main_bottleneck_phase is None


def test_progression_numbers_attempts_oldest_first():
    points = progression(history((1, "perilous-thrust"), (2, None), ("victory", 3)))

    assert [(p.attempt_number, p.phase_reached, p.result.value) for p in points] == [
        (1, 1, "failed"),
        (2, 2, "failed"),
        (3, 3, "victory"),
    ]
    assert points[0].failure_move_id == "perilous-thrust"


# ---- Through the API and PostgreSQL ----


def record(client, boss, **fields):
    resp = client.post(f"/api/bosses/{boss}/attempts", json=fields)
    assert resp.status_code == 201
    return resp.json()


def test_progression_endpoint_lists_attempts_chronologically(client):
    first = record(client, "owl-father", result="failed", phase_reached=1, failure_move_id="perilous-sweep")
    record(client, "owl-father", result="failed", phase_reached=2, failure_move_id="owl-teleport")
    record(client, "owl-father", result="victory")
    record(client, "genichiro-ashina", result="victory")

    points = client.get("/api/bosses/owl-father/progression").json()

    assert [p["attempt_number"] for p in points] == [1, 2, 3]
    assert [p["phase_reached"] for p in points] == [1, 2, 2]
    assert [p["result"] for p in points] == ["failed", "failed", "victory"]
    assert points[0]["attempt_id"] == first["id"]


def test_progression_endpoint_is_empty_without_attempts(client):
    assert client.get("/api/bosses/lady-butterfly/progression").json() == []


def test_progression_endpoint_rejects_an_unknown_boss(client):
    assert client.get("/api/bosses/nonexistent/progression").status_code == 404


def test_analytics_uses_the_requested_recent_window(client):
    for _ in range(3):
        record(client, "owl-father", result="failed", phase_reached=1, failure_move_id="perilous-sweep")
    for _ in range(2):
        record(client, "owl-father", result="failed", phase_reached=2, failure_move_id="owl-teleport")
    record(client, "owl-father", result="victory")

    default = client.get("/api/bosses/owl-father/analytics").json()
    narrow = client.get("/api/bosses/owl-father/analytics", params={"recent": 3}).json()

    assert default["recent"]["window_size"] == 10
    assert default["recent"]["total_attempts"] == 6
    assert default["attempts_until_first_victory"] == 6
    assert default["main_bottleneck_phase"] == 1

    assert narrow["recent"] == {
        "window_size": 3,
        "total_attempts": 3,
        "main_bottleneck_phase": 2,
        "most_common_failure_move": "owl-teleport",
        "failure_by_phase": {"2": 2},
        "failure_by_move": {"owl-teleport": 2},
    }


@pytest.mark.parametrize("recent", [0, -1, 101, "ten"])
def test_analytics_rejects_an_invalid_recent_window(client, recent):
    resp = client.get("/api/bosses/owl-father/analytics", params={"recent": recent})
    assert resp.status_code == 422
