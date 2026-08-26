def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_bosses(client):
    resp = client.get("/api/bosses")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "genichiro-ashina"
    assert data[0]["location"] == "Ashina Castle"


def test_get_boss(client):
    resp = client.get("/api/bosses/genichiro-ashina")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Genichiro Ashina"
    assert len(data["phases"]) == 3
    phase_1_move_ids = {m["id"] for m in data["phases"][0]["moves"]}
    assert phase_1_move_ids == {"thrust-attack", "floating-passage"}


def test_get_boss_not_found(client):
    resp = client.get("/api/bosses/nonexistent")
    assert resp.status_code == 404
