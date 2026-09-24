from typing import Literal

from pydantic import BaseModel, model_validator


class BossMove(BaseModel):
    id: str
    name: str
    move_type: str
    description: str | None = None
    telegraph: str | None = None
    counter: str | None = None
    common_mistakes: str | None = None
    name_zh: str | None = None
    # "wiki": the name used by a Chinese wiki, see name_zh_source_url.
    # "translation": translated for this app; not an official name.
    name_zh_source: Literal["wiki", "translation"] | None = None
    name_zh_source_url: str | None = None

    @model_validator(mode="after")
    def check_chinese_name_source(self) -> "BossMove":
        if (self.name_zh is None) != (self.name_zh_source is None):
            raise ValueError(f"move '{self.id}': name_zh and name_zh_source must be set together")
        if (self.name_zh_source == "wiki") != (self.name_zh_source_url is not None):
            raise ValueError(f"move '{self.id}': a wiki name needs name_zh_source_url; a translation must not have one")
        return self


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
