def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_bosses(client):
    resp = client.get("/api/bosses")
    assert resp.status_code == 200
    data = resp.json()
    boss_ids = {b["id"] for b in data}
    assert boss_ids == {
        "genichiro-ashina",
        "owl-father",
        "lady-butterfly",
        "guardian-ape",
        "corrupted-monk",
        "true-corrupted-monk",
        "great-shinobi-owl",
        "isshin-sword-saint",
    }


def test_get_boss(client):
    resp = client.get("/api/bosses/genichiro-ashina")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Genichiro Ashina"
    assert len(data["phases"]) == 3
    phase_1_move_ids = {m["id"] for m in data["phases"][0]["moves"]}
    phase_2_move_ids = {m["id"] for m in data["phases"][1]["moves"]}
    phase_3_move_ids = {m["id"] for m in data["phases"][2]["moves"]}

    # Phase 2 inherits Phase 1, except its Perilous Attack Follow Up can also end in a sweep.
    assert phase_1_move_ids - phase_2_move_ids == {"perilous-attack-follow-up"}
    assert phase_2_move_ids - phase_1_move_ids == {"perilous-attack-follow-up-phase-2"}
    # The Way of Tomoe phase has its own moveset, including three lightning attacks.
    assert phase_3_move_ids.isdisjoint(phase_2_move_ids)
    assert {"lightning-of-tomoe-shot", "lightning-of-tomoe-slash", "lightning-of-tomoe-smash"} <= phase_3_move_ids
    assert data["source_url"].endswith("/Genichiro_Ashina,_Second_Encounter")


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


def test_get_third_boss(client):
    resp = client.get("/api/bosses/lady-butterfly")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Lady Butterfly"
    assert data["source_url"] == "https://sekiroshadowsdietwice.wiki.fextralife.com/Lady+Butterfly"
    assert len(data["phases"]) == 2
    phase_1_move_ids = {m["id"] for m in data["phases"][0]["moves"]}
    phase_2_move_ids = {m["id"] for m in data["phases"][1]["moves"]}
    assert {"illusions", "phantom-kunai", "homing-butterflies"} <= phase_2_move_ids
    assert phase_1_move_ids <= phase_2_move_ids


def test_get_fourth_boss_has_a_fully_distinct_second_phase_moveset(client):
    resp = client.get("/api/bosses/guardian-ape")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Guardian Ape"
    assert len(data["phases"]) == 2
    phase_1_move_ids = {m["id"] for m in data["phases"][0]["moves"]}
    phase_2_move_ids = {m["id"] for m in data["phases"][1]["moves"]}
    # Unlike Owl (Father) and Lady Butterfly, the ape's Phase 2 form is an
    # entirely different moveset - nothing carries over from Phase 1.
    assert phase_1_move_ids.isdisjoint(phase_2_move_ids)
    assert "overhead-slam" in phase_2_move_ids


def test_get_fifth_boss_has_a_single_phase(client):
    resp = client.get("/api/bosses/corrupted-monk")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Corrupted Monk"
    assert len(data["phases"]) == 1
    assert data["phases"][0]["phase_number"] == 1
    move_ids = {m["id"] for m in data["phases"][0]["moves"]}
    assert "whirlwind-attack" in move_ids


def test_get_sixth_boss_has_a_gimmick_middle_phase(client):
    resp = client.get("/api/bosses/true-corrupted-monk")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "True Corrupted Monk"
    assert len(data["phases"]) == 3

    phase_1_move_ids = {m["id"] for m in data["phases"][0]["moves"]}
    phase_2_move_ids = {m["id"] for m in data["phases"][1]["moves"]}
    phase_3_move_ids = {m["id"] for m in data["phases"][2]["moves"]}

    # Phase 2 is a short illusion-summoning gimmick, not an extension of Phase 1.
    assert phase_2_move_ids == {"illusion-summoning"}
    # Phase 1 doesn't have the whirlwind attack yet; it's regained in Phase 3
    # along with the new centipede moves.
    assert "whirlwind-attack" not in phase_1_move_ids
    assert phase_1_move_ids <= phase_3_move_ids
    assert {"whirlwind-attack", "centipede-toxic-goo", "centipede-toxic-cloud"} <= phase_3_move_ids


def test_get_seventh_boss_replaces_backflip_with_the_poison_variant_in_phase_2(client):
    resp = client.get("/api/bosses/great-shinobi-owl")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Great Shinobi Owl"
    assert len(data["phases"]) == 2
    phase_1_move_ids = {m["id"] for m in data["phases"][0]["moves"]}
    phase_2_move_ids = {m["id"] for m in data["phases"][1]["moves"]}
    # Phase 2's Backflip only throws poison - unlike Lady Butterfly's kunai
    # upgrade, this replaces the Phase 1 shuriken variant rather than adding
    # to it.
    assert "backflip" in phase_1_move_ids
    assert "backflip" not in phase_2_move_ids
    assert "backflip-poison" in phase_2_move_ids
    assert phase_1_move_ids - {"backflip"} <= phase_2_move_ids


def test_get_eighth_boss_accumulates_moves_across_all_three_phases(client):
    resp = client.get("/api/bosses/isshin-sword-saint")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Isshin, the Sword Saint"
    assert len(data["phases"]) == 3

    phase_1_move_ids = {m["id"] for m in data["phases"][0]["moves"]}
    phase_2_move_ids = {m["id"] for m in data["phases"][1]["moves"]}
    phase_3_move_ids = {m["id"] for m in data["phases"][2]["moves"]}

    assert phase_1_move_ids <= phase_2_move_ids <= phase_3_move_ids
    assert "quad-shot" in phase_2_move_ids
    assert "lightning-slash" in phase_3_move_ids
    assert "lightning-slash" not in phase_2_move_ids


def test_get_boss_not_found(client):
    resp = client.get("/api/bosses/nonexistent")
    assert resp.status_code == 404


def test_boss_list_includes_chinese_names(client):
    names = {b["id"]: b["name_zh"] for b in client.get("/api/bosses").json()}
    assert names["genichiro-ashina"] == "苇名弦一郎"
    assert all(names.values())


def test_boss_detail_exposes_source_and_move_metadata(client):
    data = client.get("/api/bosses/isshin-sword-saint").json()
    assert data["name_zh"] == "剑圣 苇名一心"
    assert data["source_name"] == "Fextralife Sekiro Wiki"
    assert data["source_url"].endswith("/Isshin,+the+Sword+Saint")

    dragon_flash = next(m for m in data["phases"][0]["moves"] if m["id"] == "dragon-flash")
    assert "glint" in dragon_flash["telegraph"]
    assert dragon_flash["common_mistakes"]
    assert "source_url" not in dragon_flash


def test_every_boss_has_a_source(client):
    for boss in client.get("/api/bosses").json():
        detail = client.get(f"/api/bosses/{boss['id']}").json()
        assert detail["source_name"] and detail["source_url"], boss["id"]
