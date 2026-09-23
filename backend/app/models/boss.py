from pydantic import BaseModel


class BossMove(BaseModel):
    id: str
    name: str
    move_type: str
    description: str | None = None
    telegraph: str | None = None
    counter: str | None = None
    common_mistakes: str | None = None


class BossPhase(BaseModel):
    phase_number: int
    name: str
    moves: list[BossMove] = []


class Boss(BaseModel):
    id: str
    name: str
    name_zh: str | None = None
    game: str
    location: str
    phases: list[BossPhase]
    source_name: str | None = None
    source_url: str | None = None


class BossSummary(BaseModel):
    id: str
    name: str
    name_zh: str | None = None
    location: str
