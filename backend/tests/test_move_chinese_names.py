"""Chinese move names: from a Chinese wiki (with its page) or marked as translations (V3 Milestone 4)."""

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import Boss, Move
from app.models.boss import BossMove
from app.seed import SeedError, load_boss_data, sync_reference_data

WIKI_URL = "https://wiki.biligame.com/sekiro/example"


def test_every_seeded_move_has_a_chinese_name_with_a_valid_source():
    for boss in load_boss_data():
        for phase in boss.phases:
            for move in phase.moves:
                assert move.name_zh, f"{boss.id}/{move.id}"
                assert move.name_zh_source in ("wiki", "translation")
                if move.name_zh_source == "wiki":
                    assert move.name_zh_source_url.startswith("https://"), f"{boss.id}/{move.id}"


def test_seed_rejects_a_move_without_a_chinese_name(session):
    data = load_boss_data()
    move = data[0].phases[0].moves[0]
    move.name_zh = None
    move.name_zh_source = None

    with pytest.raises(SeedError, match="has no Chinese name"):
        sync_reference_data(session, data)


@pytest.mark.parametrize(
    "fields",
    [
        {"name_zh": "突刺"},
        {"name_zh_source": "translation"},
        {"name_zh": "突刺", "name_zh_source": "wiki"},
        {"name_zh": "突刺", "name_zh_source": "translation", "name_zh_source_url": WIKI_URL},
        {"name_zh": "突刺", "name_zh_source": "official"},
    ],
    ids=["name-without-source", "source-without-name", "wiki-without-page", "translation-with-page", "unknown-source"],
)
def test_move_model_rejects_inconsistent_chinese_name_sources(fields):
    with pytest.raises(ValidationError):
        BossMove(id="thrust", name="Thrust", move_type="thrust", **fields)


@pytest.mark.parametrize(
    "fields",
    [
        {"name_zh": "突刺", "name_zh_source": None},
        {"name_zh": "突刺", "name_zh_source": "wiki", "name_zh_source_url": None},
        {"name_zh": "突刺", "name_zh_source": "translation", "name_zh_source_url": WIKI_URL},
        {"name_zh": "突刺", "name_zh_source": "official"},
    ],
    ids=["name-without-source", "wiki-without-page", "translation-with-page", "unknown-source"],
)
def test_database_rejects_inconsistent_chinese_name_sources(seeded_session, fields):
    boss = seeded_session.scalar(select(Boss).where(Boss.slug == "genichiro-ashina"))
    seeded_session.add(Move(boss=boss, slug="db-check", name="Check", move_type="thrust", **fields))

    with pytest.raises(IntegrityError):
        seeded_session.flush()


def test_boss_detail_returns_chinese_names_and_their_sources(anon_client):
    boss = anon_client.get("/api/bosses/genichiro-ashina").json()
    moves = {m["id"]: m for phase in boss["phases"] for m in phase["moves"]}

    assert moves["floating-passage"]["name_zh"] == "绝技·飞渡浮舟"
    assert moves["floating-passage"]["name_zh_source"] == "wiki"
    assert moves["floating-passage"]["name_zh_source_url"].startswith("https://wiki.biligame.com/")
    assert moves["perilous-thrust"]["name_zh_source"] == "translation"
    assert moves["perilous-thrust"]["name_zh_source_url"] is None


# --- Bilingual content (V3 Milestone 4) -------------------------------------------


def test_every_english_text_field_has_a_chinese_version_and_vice_versa():
    for boss in load_boss_data():
        assert boss.location_zh, boss.id
        for phase in boss.phases:
            assert phase.name_zh, f"{boss.id} phase {phase.phase_number}"
            for move in phase.moves:
                for field in ("description", "telegraph", "counter", "common_mistakes"):
                    english, chinese = getattr(move, field), getattr(move, f"{field}_zh")
                    assert (english is None) == (chinese is None), f"{boss.id}/{move.id}.{field}"


def test_seed_rejects_english_text_without_its_chinese_version(session):
    data = load_boss_data()
    move = next(m for p in data[0].phases for m in p.moves if m.description)
    move.description_zh = None

    with pytest.raises(SeedError, match="description and description_zh must both be set"):
        sync_reference_data(session, data)


def test_seed_rejects_a_boss_without_a_chinese_location(session):
    data = load_boss_data()
    data[0].location_zh = None

    with pytest.raises(SeedError, match="has no Chinese location"):
        sync_reference_data(session, data)


def test_boss_detail_and_list_return_both_languages(anon_client):
    boss = anon_client.get("/api/bosses/genichiro-ashina").json()
    summary = next(b for b in anon_client.get("/api/bosses").json() if b["id"] == "genichiro-ashina")
    floating = next(m for m in boss["phases"][0]["moves"] if m["id"] == "floating-passage")

    assert boss["location"] and boss["location_zh"]
    assert summary["location_zh"] == boss["location_zh"]
    assert boss["phases"][0]["name_zh"] == "第一阶段"
    assert floating["description"] and floating["description_zh"]
    assert floating["common_mistakes_zh"]
