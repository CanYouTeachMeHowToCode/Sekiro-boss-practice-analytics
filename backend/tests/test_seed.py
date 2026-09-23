from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.db.models import Attempt, Boss, BossPhase, Game, Move, PhaseMove
from app.models.attempt import Attempt as V1Attempt
from app.seed import SeedError, import_v1_attempts, load_boss_data, sync_reference_data


def count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def table_counts(session):
    return {m.__tablename__: count(session, m) for m in (Game, Boss, BossPhase, Move, PhaseMove)}


def phase_move_slugs(session, boss_slug, phase_number):
    phase = session.scalar(
        select(BossPhase).join(Boss).where(Boss.slug == boss_slug, BossPhase.phase_number == phase_number)
    )
    return [link.move.slug for link in phase.move_links]


def expected_counts(data):
    """Row counts the seed data should produce, with each move stored once per boss."""
    return {
        "games": 1,
        "bosses": len(data),
        "boss_phases": sum(len(b.phases) for b in data),
        "moves": sum(len({m.id for p in b.phases for m in p.moves}) for b in data),
        "phase_moves": sum(len(p.moves) for b in data for p in b.phases),
    }


def test_sync_loads_every_boss_with_moves_stored_once(session):
    data = load_boss_data()
    sync_reference_data(session, data)

    counts = table_counts(session)
    assert counts == expected_counts(data)
    # Moves shared across phases are stored once, so there are fewer moves than phase-move links.
    assert counts["moves"] < counts["phase_moves"]


def test_sync_is_idempotent(session):
    sync_reference_data(session, load_boss_data())
    first = table_counts(session)

    report = sync_reference_data(session, load_boss_data())

    assert table_counts(session) == first
    assert report.warnings == []


def test_sync_preserves_move_order_within_a_phase(session):
    data = load_boss_data()
    sync_reference_data(session, data)

    owl = next(b for b in data if b.id == "owl-father")
    for phase in owl.phases:
        assert phase_move_slugs(session, "owl-father", phase.phase_number) == [m.id for m in phase.moves]


def test_sync_applies_edits_to_existing_rows(session):
    data = load_boss_data()
    sync_reference_data(session, data)

    genichiro = next(b for b in data if b.id == "genichiro-ashina")
    for phase in genichiro.phases:
        for move in phase.moves:
            if move.id == "floating-passage":
                move.counter = "Deflect every hit."
    sync_reference_data(session, data)

    move = session.scalar(select(Move).join(Boss).where(Boss.slug == "genichiro-ashina", Move.slug == "floating-passage"))
    assert move.counter == "Deflect every hit."
    assert count(session, Move) == expected_counts(data)["moves"]


def test_sync_reports_but_keeps_moves_removed_from_the_seed_data(session):
    data = load_boss_data()
    sync_reference_data(session, data)

    genichiro = next(b for b in data if b.id == "genichiro-ashina")
    for phase in genichiro.phases:
        phase.moves = [m for m in phase.moves if m.id != "lightning-of-tomoe-smash"]
    report = sync_reference_data(session, data)

    # The move still exists (attempts may reference it) but no longer appears in any phase.
    assert session.scalar(select(Move).join(Boss).where(Boss.slug == "genichiro-ashina", Move.slug == "lightning-of-tomoe-smash"))
    assert "lightning-of-tomoe-smash" not in phase_move_slugs(session, "genichiro-ashina", 3)
    assert any("lightning-of-tomoe-smash" in w for w in report.warnings)


def test_sync_rejects_a_move_described_differently_across_phases(session):
    data = load_boss_data()
    owl = next(b for b in data if b.id == "owl-father")
    owl.phases[1].moves[0].description = "Something else"

    with pytest.raises(SeedError, match="differs between phase 1 and phase 2"):
        sync_reference_data(session, data)
    assert count(session, Boss) == 0


def test_sync_rejects_an_unknown_game(session):
    data = load_boss_data()
    data[0].game = "elden-ring"

    with pytest.raises(SeedError, match="unknown game"):
        sync_reference_data(session, data)


def v1_attempt(**overrides):
    fields = {
        "id": "attempt-001",
        "boss_id": "genichiro-ashina",
        "timestamp": datetime(2026, 8, 26, 19, 37, tzinfo=timezone.utc),
        "result": "failed",
        "phase_reached": 2,
        "failure_move_id": "floating-passage",
        "failure_category": None,
        "notes": "",
    }
    return V1Attempt.model_validate({**fields, **overrides})


def test_import_v1_attempts_maps_moves_and_keeps_timestamps(seeded_session):
    history = [
        v1_attempt(),
        v1_attempt(
            id="attempt-002",
            timestamp=datetime(2026, 8, 26, 19, 40, tzinfo=timezone.utc),
            result="failed",
            phase_reached=1,
            failure_move_id=None,
            failure_category="not_sure",
        ),
        v1_attempt(
            id="attempt-003",
            boss_id="owl-father",
            timestamp=datetime(2026, 8, 26, 19, 45, tzinfo=timezone.utc),
            result="victory",
            phase_reached=2,
            failure_move_id=None,
        ),
    ]

    assert import_v1_attempts(seeded_session, history) == 3

    rows = seeded_session.scalars(select(Attempt).order_by(Attempt.created_at)).all()
    assert [r.boss.slug for r in rows] == ["genichiro-ashina", "genichiro-ashina", "owl-father"]
    assert rows[0].failure_move.slug == "floating-passage"
    assert rows[0].created_at == datetime(2026, 8, 26, 19, 37, tzinfo=timezone.utc)
    assert rows[1].failure_move is None and rows[1].failure_category == "not_sure"
    assert rows[2].result == "victory"


def test_import_v1_attempts_refuses_to_run_twice(seeded_session):
    import_v1_attempts(seeded_session, [v1_attempt()])

    with pytest.raises(SeedError, match="already has 1 rows"):
        import_v1_attempts(seeded_session, [v1_attempt(id="attempt-002")])
    assert count(seeded_session, Attempt) == 1


def test_import_v1_attempts_rejects_a_move_from_another_boss(seeded_session):
    with pytest.raises(SeedError, match="does not belong to boss"):
        import_v1_attempts(seeded_session, [v1_attempt(failure_move_id="shadowfall")])
