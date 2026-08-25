def test_create_attempt_with_valid_move(client):
    resp = client.post(
        "/api/bosses/genichiro-ashina/attempts",
        json={"result": "failed", "phase_reached": 1, "failure_move_id": "floating-passage"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["failure_move_id"] == "floating-passage"
    assert data["failure_category"] is None


def test_create_attempt_invalid_boss(client):
    resp = client.post(
        "/api/bosses/nonexistent/attempts",
        json={"result": "failed", "phase_reached": 1},
    )
    assert resp.status_code == 404


def test_create_attempt_invalid_phase(client):
    resp = client.post(
        "/api/bosses/genichiro-ashina/attempts",
        json={"result": "failed", "phase_reached": 99},
    )
    assert resp.status_code == 400


def test_create_victory_without_failure_move(client):
    resp = client.post(
        "/api/bosses/genichiro-ashina/attempts",
        json={"result": "victory", "phase_reached": 3},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["failure_move_id"] is None
    assert data["failure_category"] is None


def test_create_failed_attempt_not_sure(client):
    resp = client.post(
        "/api/bosses/genichiro-ashina/attempts",
        json={"result": "failed", "phase_reached": 2},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["failure_move_id"] is None
    assert data["failure_category"] == "not_sure"


def test_create_attempt_move_not_belonging_to_boss(client):
    resp = client.post(
        "/api/bosses/genichiro-ashina/attempts",
        json={"result": "failed", "phase_reached": 1, "failure_move_id": "does-not-exist"},
    )
    assert resp.status_code == 400


def test_attempt_history_order(client):
    client.post(
        "/api/bosses/genichiro-ashina/attempts",
        json={"result": "failed", "phase_reached": 1, "failure_move_id": "thrust-attack"},
    )
    client.post(
        "/api/bosses/genichiro-ashina/attempts",
        json={"result": "failed", "phase_reached": 2, "failure_move_id": "floating-passage"},
    )

    resp = client.get("/api/bosses/genichiro-ashina/attempts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["phase_reached"] == 2
    assert data[1]["phase_reached"] == 1


def test_analytics_aggregation(client):
    attempts = [
        {"result": "failed", "phase_reached": 1, "failure_move_id": "thrust-attack"},
        {"result": "failed", "phase_reached": 2, "failure_move_id": "floating-passage"},
        {"result": "failed", "phase_reached": 2, "failure_move_id": "floating-passage"},
        {"result": "failed", "phase_reached": 3, "failure_move_id": "lightning-attack"},
        {"result": "victory", "phase_reached": 3},
    ]
    for attempt in attempts:
        resp = client.post("/api/bosses/genichiro-ashina/attempts", json=attempt)
        assert resp.status_code == 201

    resp = client.get("/api/bosses/genichiro-ashina/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_attempts"] == 5
    assert data["defeated"] is True
    assert data["best_phase"] == 3
    assert data["main_bottleneck_phase"] == 2
    assert data["most_common_failure_move"] == "floating-passage"
    assert data["failure_by_phase"]["2"] == 2
    assert data["failure_by_move"]["floating-passage"] == 2
