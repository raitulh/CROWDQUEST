import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SessionStatus(str, enum.Enum):
    CREATED = "created"
    READY = "ready"
    VOTING = "voting"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ENDED = "ended"


class RoundStatus(str, enum.Enum):
    READY = "ready"
    VOTING = "voting"
    VOTE_LOCKED = "vote_locked"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    twitch_user_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    login: Mapped[str] = mapped_column(String(100), index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    profile_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferences_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    twitch_connection: Mapped["TwitchConnection | None"] = relationship(back_populates="user", uselist=False)
    sessions: Mapped[list["CrowdSession"]] = relationship(back_populates="owner")


class TwitchConnection(Base):
    __tablename__ = "twitch_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    access_token_ciphertext: Mapped[str] = mapped_column(Text)
    refresh_token_ciphertext: Mapped[str] = mapped_column(Text)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="connected")
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="twitch_connection")


class CrowdSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_broadcaster_status", "broadcaster_user_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    broadcaster_user_id: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(160), default="Community Quest")
    status: Mapped[str] = mapped_column(String(30), default=SessionStatus.CREATED.value, index=True)
    current_round_id: Mapped[str | None] = mapped_column(
        ForeignKey("quest_rounds.id", ondelete="SET NULL", use_alter=True, name="fk_sessions_current_round"),
        nullable=True,
    )
    overlay_token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    community_xp: Mapped[int] = mapped_column(Integer, default=0)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped[User] = relationship(back_populates="sessions")
    rounds: Mapped[list["QuestRound"]] = relationship(back_populates="session", cascade="all, delete-orphan", foreign_keys="QuestRound.session_id")


class QuestRound(Base):
    __tablename__ = "quest_rounds"
    __table_args__ = (Index("ix_quest_rounds_session_state", "session_id", "state"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    narrative: Mapped[str] = mapped_column(Text)
    success_message: Mapped[str] = mapped_column(String(240), default="The community succeeds.")
    failure_message: Mapped[str] = mapped_column(String(240), default="The objective remains unfinished.")
    theme: Mapped[str] = mapped_column(String(80))
    difficulty: Mapped[str] = mapped_column(String(20))
    options_json: Mapped[list[dict]] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(30), default=RoundStatus.READY.value)
    winning_option_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    objective_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    objective_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    objective_duration_seconds: Mapped[int] = mapped_column(Integer, default=120)
    objective_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    objective_progress: Mapped[int] = mapped_column(Integer, default=0)
    reward_xp: Mapped[int] = mapped_column(Integer, default=100)
    vote_duration_seconds: Mapped[int] = mapped_column(Integer, default=45)
    vote_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[CrowdSession] = relationship(back_populates="rounds", foreign_keys=[session_id])
    votes: Mapped[list["Vote"]] = relationship(back_populates="round", cascade="all, delete-orphan")
    contributions: Mapped[list["Contribution"]] = relationship(back_populates="round", cascade="all, delete-orphan")


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("round_id", "viewer_twitch_id", name="uq_vote_round_viewer"),
        Index("ix_votes_round_option", "round_id", "option_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    round_id: Mapped[str] = mapped_column(ForeignKey("quest_rounds.id", ondelete="CASCADE"), index=True)
    viewer_twitch_id: Mapped[str] = mapped_column(String(32))
    viewer_login: Mapped[str] = mapped_column(String(100))
    option_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    round: Mapped[QuestRound] = relationship(back_populates="votes")


class Contribution(Base):
    __tablename__ = "contributions"
    __table_args__ = (
        UniqueConstraint("round_id", "viewer_twitch_id", "contribution_type", name="uq_contribution_round_viewer_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    round_id: Mapped[str] = mapped_column(ForeignKey("quest_rounds.id", ondelete="CASCADE"), index=True)
    viewer_twitch_id: Mapped[str] = mapped_column(String(32))
    viewer_login: Mapped[str] = mapped_column(String(100))
    contribution_type: Mapped[str] = mapped_column(String(40))
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    round: Mapped[QuestRound] = relationship(back_populates="contributions")


class ProcessedEvent(Base):
    __tablename__ = "processed_events"
    __table_args__ = (Index("ix_processed_events_processed_at", "processed_at"),)

    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SessionEvent(Base):
    __tablename__ = "session_events"
    __table_args__ = (Index("ix_session_events_session_created", "session_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
