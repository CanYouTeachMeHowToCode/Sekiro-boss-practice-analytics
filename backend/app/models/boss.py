from pydantic import BaseModel


class BossMove(BaseModel):
    id: str
    name: str
    move_type: str
    description: str | None = None
    counter: str | None = None


class BossPhase(BaseModel):
    phase_number: int
    name: str
    moves: list[BossMove] = []


class Boss(BaseModel):
    id: str
    name: str
    game: str
    location: str
    phases: list[BossPhase]
    source_url: str | None = None


class BossSummary(BaseModel):
    id: str
    name: str
    location: str
