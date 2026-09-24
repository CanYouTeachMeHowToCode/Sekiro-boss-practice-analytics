"""Load reference data (bosses, phases, moves) and V1 attempt history into PostgreSQL."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Attempt, Boss, BossPhase, Game, Move, PhaseMove
from app.models.attempt import Attempt as V1Attempt
from app.models.boss import Boss as BossData

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
BOSSES_FILE = SEED_DIR / "bosses.json"

GAMES = {"sekiro": "Sekiro: Shadows Die Twice"}

MOVE_FIELDS = (
    "name",
    "move_type",
    "description",
    "telegraph",
    "counter",
    "common_mistakes",
    "name_zh",
    "name_zh_source",
    "name_zh_source_url",
    "description_zh",
    "telegraph_zh",
    "counter_zh",
    "common_mistakes_zh",
)

# Every English text field that has a value needs its Chinese version.
TRANSLATED_MOVE_FIELDS = ("description", "telegraph", "counter", "common_mistakes")


class SeedError(ValueError):
    pass


@dataclass
class SyncReport:
    bosses: int = 0
    phases: int = 0
    moves: int = 0
    phase_moves: int = 0
    warnings: list[str] = field(default_factory=list)


def load_boss_data(path: Path = BOSSES_FILE) -> list[BossData]:
    with open(path, encoding="utf-8") as f:
        return [BossData.model_validate(entry) for entry in json.load(f)]


def _validate(bosses: list[BossData]) -> None:
    errors = []
    slugs = [b.id for b in bosses]
    for slug in {s for s in slugs if slugs.count(s) > 1}:
        errors.append(f"boss '{slug}' is defined more than once")

    for boss in bosses:
        if boss.game not in GAMES:
            errors.append(f"boss '{boss.id}' references unknown game '{boss.game}'")

        if boss.location_zh is None:
            errors.append(f"boss '{boss.id}' has no Chinese location (location_zh)")
        for phase in boss.phases:
            if phase.name_zh is None:
                errors.append(f"boss '{boss.id}' phase {phase.phase_number} has no Chinese name (name_zh)")

        numbers = [p.phase_number for p in boss.phases]
        if len(numbers) != len(set(numbers)):
            errors.append(f"boss '{boss.id}' has duplicate phase numbers")

        first_seen: dict[str, tuple[int, dict]] = {}
        for phase in boss.phases:
            move_ids = [m.id for m in phase.moves]
            if len(move_ids) != len(set(move_ids)):
                errors.append(f"boss '{boss.id}' phase {phase.phase_number} lists a move twice")
            for move in phase.moves:
                if move.name_zh is None:
                    errors.append(f"boss '{boss.id}' move '{move.id}' has no Chinese name (name_zh)")
                for field_name in TRANSLATED_MOVE_FIELDS:
                    has_english = getattr(move, field_name) is not None
                    has_chinese = getattr(move, f"{field_name}_zh") is not None
                    if has_english != has_chinese:
                        errors.append(
                            f"boss '{boss.id}' move '{move.id}': {field_name} and {field_name}_zh must both be set or both be empty"
                        )
                data = move.model_dump(include=set(MOVE_FIELDS))
                if move.id not in first_seen:
                    first_seen[move.id] = (phase.phase_number, data)
                elif first_seen[move.id][1] != data:
                    # A move is stored once, so every phase must describe it identically.
                    earlier = first_seen[move.id][0]
                    diff = [k for k in MOVE_FIELDS if data[k] != first_seen[move.id][1][k]]
                    errors.append(
                        f"boss '{boss.id}' move '{move.id}' differs between phase {earlier} "
                        f"and phase {phase.phase_number} in {diff}"
                    )

    if errors:
        raise SeedError("Invalid boss seed data:\n  " + "\n  ".join(errors))


def sync_reference_data(session: Session, bosses: list[BossData]) -> SyncReport:
    """Insert or update bosses, phases, and moves so the database matches the seed data.

    Safe to run repeatedly. Bosses, phases, and moves that are no longer in the
    seed data are reported but never deleted, because attempt history may
    reference them. Which moves appear in which phase is fully replaced.
    """
    _validate(bosses)
    report = SyncReport()

    games = {}
    for slug, name in GAMES.items():
        game = session.scalar(select(Game).where(Game.slug == slug))
        if game is None:
            game = Game(slug=slug)
            session.add(game)
        game.name = name
        games[slug] = game

    seed_slugs = {b.id for b in bosses}
    for (slug,) in session.execute(select(Boss.slug)):
        if slug not in seed_slugs:
            report.warnings.append(f"boss '{slug}' is in the database but not in the seed data")

    for data in bosses:
        boss = session.scalar(select(Boss).where(Boss.slug == data.id))
        if boss is None:
            boss = Boss(slug=data.id)
            session.add(boss)
        boss.game = games[data.game]
        boss.name = data.name
        boss.name_zh = data.name_zh
        boss.location = data.location
        boss.location_zh = data.location_zh
        boss.source_name = data.source_name
        boss.source_url = data.source_url
        report.bosses += 1

        moves_by_slug = {m.slug: m for m in boss.moves}
        seen_moves: set[str] = set()
        for phase_data in data.phases:
            for move_data in phase_data.moves:
                if move_data.id in seen_moves:
                    continue
                seen_moves.add(move_data.id)
                move = moves_by_slug.get(move_data.id)
                if move is None:
                    move = Move(slug=move_data.id)
                    boss.moves.append(move)
                    moves_by_slug[move.slug] = move
                for name in MOVE_FIELDS:
                    setattr(move, name, getattr(move_data, name))
                report.moves += 1
        for slug in moves_by_slug.keys() - seen_moves:
            report.warnings.append(f"move '{data.id}/{slug}' is in the database but not in the seed data")

        phases_by_number = {p.phase_number: p for p in boss.phases}
        for phase_data in data.phases:
            phase = phases_by_number.get(phase_data.phase_number)
            if phase is None:
                phase = BossPhase(phase_number=phase_data.phase_number)
                boss.phases.append(phase)
            phase.name = phase_data.name
            phase.name_zh = phase_data.name_zh
            report.phases += 1

            phase.move_links.clear()
            session.flush()
            for position, move_data in enumerate(phase_data.moves):
                phase.move_links.append(PhaseMove(move=moves_by_slug[move_data.id], position=position))
                report.phase_moves += 1
        seed_numbers = {p.phase_number for p in data.phases}
        for number in phases_by_number.keys() - seed_numbers:
            report.warnings.append(f"phase '{data.id}/{number}' is in the database but not in the seed data")

    session.flush()
    return report


def load_v1_attempts(path: Path) -> list[V1Attempt]:
    with open(path, encoding="utf-8") as f:
        return [V1Attempt.model_validate(entry) for entry in json.load(f)]


def import_v1_attempts(session: Session, attempts: list[V1Attempt]) -> int:
    """Copy V1 attempt history into the attempts table, preserving timestamps and order.

    Runs only against an empty attempts table so it can't duplicate history if
    it is accidentally run twice.
    """
    existing = session.scalar(select(func.count()).select_from(Attempt))
    if existing:
        raise SeedError(f"attempts table already has {existing} rows; refusing to import V1 history again")

    bosses = {b.slug: b for b in session.scalars(select(Boss))}
    for v1 in sorted(attempts, key=lambda a: a.timestamp):
        boss = bosses.get(v1.boss_id)
        if boss is None:
            raise SeedError(f"{v1.id}: unknown boss '{v1.boss_id}'")
        move = None
        if v1.failure_move_id is not None:
            move = next((m for m in boss.moves if m.slug == v1.failure_move_id), None)
            if move is None:
                raise SeedError(f"{v1.id}: move '{v1.failure_move_id}' does not belong to boss '{v1.boss_id}'")
        session.add(
            Attempt(
                boss=boss,
                result=v1.result.value,
                phase_reached=v1.phase_reached,
                failure_move=move,
                failure_category=v1.failure_category.value if v1.failure_category else None,
                notes=v1.notes,
                created_at=v1.timestamp,
            )
        )
    session.flush()
    return len(attempts)
