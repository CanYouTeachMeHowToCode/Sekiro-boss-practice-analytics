import json
from pathlib import Path

from app.models.boss import Boss, BossMove, BossSummary

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BOSSES_FILE = "bosses.json"


def _load_bosses() -> list[Boss]:
    path = DATA_DIR / BOSSES_FILE
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Boss.model_validate(entry) for entry in raw]


def get_all_bosses() -> list[BossSummary]:
    return [
        BossSummary(id=boss.id, name=boss.name, location=boss.location)
        for boss in _load_bosses()
    ]


def get_boss(boss_id: str) -> Boss | None:
    for boss in _load_bosses():
        if boss.id == boss_id:
            return boss
    return None


def get_move(boss_id: str, move_id: str) -> BossMove | None:
    boss = get_boss(boss_id)
    if boss is None:
        return None
    for phase in boss.phases:
        for move in phase.moves:
            if move.id == move_id:
                return move
    return None


def phase_exists(boss_id: str, phase_number: int) -> bool:
    boss = get_boss(boss_id)
    if boss is None:
        return False
    return any(phase.phase_number == phase_number for phase in boss.phases)
