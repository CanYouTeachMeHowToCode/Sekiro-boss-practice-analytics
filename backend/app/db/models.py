from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
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
        CheckConstraint("(source_name IS NULL) = (source_url IS NULL)", name="ck_moves_source_complete"),
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
    # Only for a move whose data comes from a different page than its boss's;
    # null means the move uses the boss's source_name / source_url.
    source_name: Mapped[str | None] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(Text)
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
    # NOT NULL since V3.1: attempts recorded before accounts existed had to be claimed with
    # `python -m scripts.claim_attempts <username>` before that migration.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    result: Mapped[str] = mapped_column(String(20))
    phase_reached: Mapped[int] = mapped_column(Integer)
    failure_move_id: Mapped[int | None] = mapped_column(ForeignKey("moves.id", ondelete="RESTRICT"))
    failure_category: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    boss: Mapped[Boss] = relationship()
    user: Mapped["User"] = relationship()
    failure_move: Mapped[Move | None] = relationship()



RECORDING_STATUSES = ("uploaded", "checking", "rejected", "queued", "processing", "done", "failed")
FAILURE_TYPES = ("damage", "posture_break", "death")


class Recording(Base):
    """A fight recording a user uploaded for the failure report (V4 Milestone 3).

    The video stays on disk under RECORDINGS_DIR; only its metadata and path are stored here. The worker moves it
    through the statuses: uploaded -> checking -> rejected (reject_code says why) or queued -> processing -> done
    (or failed).
    """

    __tablename__ = "recordings"
    __table_args__ = (
        CheckConstraint(
            "status IN (" + ", ".join(f"'{s}'" for s in RECORDING_STATUSES) + ")", name="ck_recordings_status"
        ),
        CheckConstraint("progress >= 0 AND progress <= 1", name="ck_recordings_progress"),
        CheckConstraint("status = 'rejected' OR reject_code IS NULL", name="ck_recordings_reject_code_only_if_rejected"),
        # The list shows one user's recordings, newest first; the worker looks for work by status.
        Index("ix_recordings_user_id_created_at", "user_id", "created_at"),
        Index("ix_recordings_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    boss_id: Mapped[int] = mapped_column(ForeignKey("bosses.id", ondelete="RESTRICT"))
    original_filename: Mapped[str] = mapped_column(String(255))
    # relative to RECORDINGS_DIR
    storage_path: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="uploaded", server_default="uploaded")
    # why a recording was rejected, as a code the frontend translates (e.g. too_long, not_genichiro)
    reject_code: Mapped[str | None] = mapped_column(String(40))
    # processing progress, 0 to 1, and an error for the logs when processing failed
    progress: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    error: Mapped[str | None] = mapped_column(Text)
    # filled in by the worker's check
    duration_s: Mapped[float | None] = mapped_column(Float)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    fps: Mapped[float | None] = mapped_column(Float)
    # the frozen pipeline version that produced the failures
    pipeline_version: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship()
    boss: Mapped[Boss] = relationship()
    failures: Mapped[list["RecordingFailure"]] = relationship(
        back_populates="recording", cascade="all, delete-orphan", order_by="RecordingFailure.time_s"
    )


class RecordingFailure(Base):
    """One failure found in a recording: damage, a posture break or a death, with the move behind it.

    move_id is set only when the system is sure of the move (sure); otherwise candidates holds the moves it could be,
    best first, and the report says the move is uncertain.
    """

    __tablename__ = "recording_failures"
    __table_args__ = (
        CheckConstraint("type IN (" + ", ".join(f"'{t}'" for t in FAILURE_TYPES) + ")", name="ck_recording_failures_type"),
        CheckConstraint("sure OR move_id IS NULL", name="ck_recording_failures_move_only_if_sure"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    recording_id: Mapped[int] = mapped_column(ForeignKey("recordings.id", ondelete="CASCADE"), index=True)
    time_s: Mapped[float] = mapped_column(Float)
    type: Mapped[str] = mapped_column(String(20))
    phase: Mapped[int] = mapped_column(Integer)
    sure: Mapped[bool] = mapped_column(Boolean)
    move_id: Mapped[int | None] = mapped_column(ForeignKey("moves.id", ondelete="RESTRICT"))
    # [{"move": slug, "score": float}, ...], best first
    candidates: Mapped[list] = mapped_column(JSON, default=list)
    # the events merged into this failure: [{"type": ..., "time_s": ...}, ...]
    events: Mapped[list] = mapped_column(JSON, default=list)
    # relative to RECORDINGS_DIR; null until the clip is cut
    clip_path: Mapped[str | None] = mapped_column(Text)

    recording: Mapped[Recording] = relationship(back_populates="failures")
    move: Mapped[Move | None] = relationship()

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
