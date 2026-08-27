def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_bosses(client):
    resp = client.get("/api/bosses")
    assert resp.status_code == 200
    data = resp.json()
    boss_ids = {b["id"] for b in data}
    assert boss_ids == {"genichiro-ashina", "owl-father"}


def test_get_boss(client):
    resp = client.get("/api/bosses/genichiro-ashina")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Genichiro Ashina"
    assert len(data["phases"]) == 3
    phase_1_move_ids = {m["id"] for m in data["phases"][0]["moves"]}
    assert phase_1_move_ids == {"normal-attack", "bow-attack", "thrust-attack", "floating-passage"}


def test_get_second_boss(client):
    resp = client.get("/api/bosses/owl-father")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Owl (Father)"
    assert len(data["phases"]) == 2
    phase_1_move_ids = {m["id"] for m in data["phases"][0]["moves"]}
    phase_2_move_ids = {m["id"] for m in data["phases"][1]["moves"]}
    assert {"owl-teleport", "backflip-shuriken", "fire-owl-shadowfall"} <= phase_2_move_ids
    assert phase_1_move_ids <= phase_2_move_ids


def test_get_boss_not_found(client):
    resp = client.get("/api/bosses/nonexistent")
    assert resp.status_code == 404
