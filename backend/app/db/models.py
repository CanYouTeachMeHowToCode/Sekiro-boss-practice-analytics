from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))

    bosses: Mapped[list["Boss"]] = relationship(back_populates="game")


class Boss(Base):
    __tablename__ = "bosses"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="RESTRICT"))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    name_zh: Mapped[str | None] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(200))
    location_zh: Mapped[str | None] = mapped_column(String(200))
    # Where this boss's phase and move data came from; moves share their boss's source.
    source_name: Mapped[str | None] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(Text)

    game: Mapped[Game] = relationship(back_populates="bosses")
    phases: Mapped[list["BossPhase"]] = relationship(
        back_populates="boss", order_by="BossPhase.phase_number", cascade="all, delete-orphan"
    )
    moves: Mapped[list["Move"]] = relationship(back_populates="boss", cascade="all, delete-orphan")


class BossPhase(Base):
    __tablename__ = "boss_phases"
    __table_args__ = (UniqueConstraint("boss_id", "phase_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    boss_id: Mapped[int] = mapped_column(ForeignKey("bosses.id", ondelete="CASCADE"))
    phase_number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(100))
    name_zh: Mapped[str | None] = mapped_column(String(100))

    boss: Mapped[Boss] = relationship(back_populates="phases")
    move_links: Mapped[list["PhaseMove"]] = relationship(
        back_populates="phase", order_by="PhaseMove.position", cascade="all, delete-orphan"
    )


class Move(Base):
    __tablename__ = "moves"
    __table_args__ = (
        UniqueConstraint("boss_id", "slug"),
        CheckConstraint(
            "name_zh_source IS NULL OR name_zh_source IN ('wiki', 'translation')",
            name="ck_moves_name_zh_source",
        ),
        CheckConstraint("(name_zh IS NULL) = (name_zh_source IS NULL)", name="ck_moves_name_zh_has_source"),
        # A name taken from a Chinese wiki must say which page; a translation has no page.
        CheckConstraint(
            "(name_zh_source = 'wiki') = (name_zh_source_url IS NOT NULL)", name="ck_moves_name_zh_source_url"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    boss_id: Mapped[int] = mapped_column(ForeignKey("bosses.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    move_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    telegraph: Mapped[str | None] = mapped_column(Text)
    counter: Mapped[str | None] = mapped_column(Text)
    common_mistakes: Mapped[str | None] = mapped_column(Text)
    # Chinese versions of the text fields above: translations of the sourced English text.
    description_zh: Mapped[str | None] = mapped_column(Text)
    telegraph_zh: Mapped[str | None] = mapped_column(Text)
    counter_zh: Mapped[str | None] = mapped_column(Text)
    common_mistakes_zh: Mapped[str | None] = mapped_column(Text)
    # Chinese name: either the name used by a Chinese wiki ('wiki', with the page in
    # name_zh_source_url) or a translation ('translation'), never presented as official.
    name_zh: Mapped[str | None] = mapped_column(String(200))
    name_zh_source: Mapped[str | None] = mapped_column(String(20))
    name_zh_source_url: Mapped[str | None] = mapped_column(Text)

    boss: Mapped[Boss] = relationship(back_populates="moves")
    phase_links: Mapped[list["PhaseMove"]] = relationship(back_populates="move", cascade="all, delete-orphan")


class PhaseMove(Base):
    """Which moves appear in which phase, and in what order."""

    __tablename__ = "phase_moves"

    boss_phase_id: Mapped[int] = mapped_column(ForeignKey("boss_phases.id", ondelete="CASCADE"), primary_key=True)
    move_id: Mapped[int] = mapped_column(ForeignKey("moves.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)

    phase: Mapped[BossPhase] = relationship(back_populates="move_links")
    move: Mapped[Move] = relationship(back_populates="phase_links")


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = (
        CheckConstraint("result IN ('failed', 'victory')", name="ck_attempts_result"),
        CheckConstraint(
            "failure_category IS NULL OR failure_category IN ('other', 'not_sure')",
            name="ck_attempts_failure_category",
        ),
        CheckConstraint(
            "result = 'failed' OR (failure_move_id IS NULL AND failure_category IS NULL)",
            name="ck_attempts_victory_has_no_failure",
        ),
        CheckConstraint(
            "failure_move_id IS NULL OR failure_category IS NULL",
            name="ck_attempts_single_failure_cause",
        ),
        # Every attempt query filters by user and boss.
        Index("ix_attempts_user_id_boss_id", "user_id", "boss_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    boss_id: Mapped[int] = mapped_column(ForeignKey("bosses.id", ondelete="RESTRICT"), index=True)
    # Null only for attempts recorded before accounts existed. They are visible to
    # nobody until `python -m scripts.claim_attempts <username>` assigns them.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    result: Mapped[str] = mapped_column(String(20))
    phase_reached: Mapped[int] = mapped_column(Integer)
    failure_move_id: Mapped[int | None] = mapped_column(ForeignKey("moves.id", ondelete="RESTRICT"))
    failure_category: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    boss: Mapped[Boss] = relationship()
    user: Mapped["User | None"] = relationship()
    failure_move: Mapped[Move | None] = relationship()


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("username = lower(username)", name="ck_users_username_lowercase"),
        CheckConstraint(
            "preferred_language IS NULL OR preferred_language IN ('en', 'zh')", name="ck_users_preferred_language"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stored lowercase so usernames are unique regardless of case.
    username: Mapped[str] = mapped_column(String(30), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # Interface language chosen in the app; null until the user picks one.
    preferred_language: Mapped[str | None] = mapped_column(String(5))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """A login session. Only a SHA-256 hash of the cookie token is stored."""

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")
