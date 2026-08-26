import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.models.attempt import Attempt, AttemptResult, CreateAttemptRequest, FailureCategory
from app.services import boss_service

DATA_DIR = Path(os.environ.get("SEKIRO_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data")))
ATTEMPTS_FILE = "attempts.json"


class AttemptValidationError(ValueError):
    pass


def _attempts_path() -> Path:
    return DATA_DIR / ATTEMPTS_FILE


def _load_all_attempts() -> list[Attempt]:
    path = _attempts_path()
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Attempt.model_validate(entry) for entry in raw]


def _save_all_attempts(attempts: list[Attempt]) -> None:
    path = _attempts_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump([a.model_dump(mode="json") for a in attempts], f, indent=2)


def get_attempts(boss_id: str) -> list[Attempt]:
    attempts = [a for a in _load_all_attempts() if a.boss_id == boss_id]
    return list(reversed(attempts))


def create_attempt(boss_id: str, req: CreateAttemptRequest) -> Attempt:
    if not boss_service.phase_exists(boss_id, req.phase_reached):
        raise AttemptValidationError(
            f"Phase {req.phase_reached} does not exist for boss '{boss_id}'"
        )

    failure_move_id = req.failure_move_id
    failure_category = req.failure_category

    if req.result == AttemptResult.VICTORY:
        failure_move_id = None
        failure_category = None
    else:
        if failure_move_id is not None:
            if boss_service.get_move(boss_id, failure_move_id) is None:
                raise AttemptValidationError(
                    f"Move '{failure_move_id}' does not belong to boss '{boss_id}'"
                )
            failure_category = None
        elif failure_category is None:
            failure_category = FailureCategory.NOT_SURE

    all_attempts = _load_all_attempts()
    attempt = Attempt(
        id=f"attempt-{len(all_attempts) + 1:03d}",
        boss_id=boss_id,
        timestamp=datetime.now(timezone.utc),
        result=req.result,
        phase_reached=req.phase_reached,
        failure_move_id=failure_move_id,
        failure_category=failure_category,
        notes=req.notes or "",
    )
    all_attempts.append(attempt)
    _save_all_attempts(all_attempts)
    return attempt
