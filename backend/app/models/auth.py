import re

from pydantic import BaseModel, Field, field_validator

USERNAME_PATTERN = r"^[a-z0-9_-]+$"


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    # Upper bound keeps a single request from making argon2 hash megabytes of input.
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("username")
    @classmethod
    def check_username_characters(cls, value: str) -> str:
        if not re.fullmatch(USERNAME_PATTERN, value):
            raise ValueError("Username may only contain letters, digits, '_' and '-'")
        return value


class LoginRequest(BaseModel):
    username: str = Field(max_length=100)
    password: str = Field(max_length=128)


class User(BaseModel):
    id: str
    username: str
