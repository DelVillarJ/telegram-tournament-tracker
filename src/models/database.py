"""Database models for storing tournament data and notifications."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import uuid
from datetime import datetime


class Base(DeclarativeBase):
    """Declarative base for bot persistence models."""


class Tournament(Base):
    """Model for tracking TopDeck tournaments."""
    
    __tablename__ = "tournaments"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tournament_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")

    participant_count: Mapped[int] = mapped_column(Integer, default=0)
    max_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)

    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_notified: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=lambda: datetime.utcnow(),
    )

    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="tournament",
        cascade="all, delete-orphan",
    )
    standings: Mapped[list["Standings"]] = relationship(
        back_populates="tournament",
        cascade="all, delete-orphan",
    )
    
    def is_complete(self):
        """Check if tournament is complete."""
        return self.status.lower() in ["completed", "finished", "ended"]


class Standings(Base):
    """Model for tournament standings/leaderboard."""
    
    __tablename__ = "standings"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tournament_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("tournaments.tournament_id"),
        nullable=False,
    )
    player_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    player_name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=0)
    undefeated_bonus: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    wins: Mapped[int] = mapped_column(Integer, default=0)
    matches_played: Mapped[int] = mapped_column(Integer, default=0)

    tournament: Mapped["Tournament"] = relationship(back_populates="standings")


class BonusAdjustment(Base):
    """Model for manually adjusting a player's cumulative league points."""

    __tablename__ = "bonus_adjustments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id = Column(String(100), nullable=False, index=True)
    player_name = Column(String(100), nullable=False)
    points = Column(Integer, nullable=False)
    added_by = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.utcnow())


class Admin(Base):
    """Model for Telegram accounts allowed to manage the bot."""

    __tablename__ = "admins"

    identifier: Mapped[str] = mapped_column(String(100), primary_key=True)
    added_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
    )


class TournamentChannel(Base):
    """Telegram destination assigned to a TopDeck tournament."""

    __tablename__ = "tournament_channels"

    tournament_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    chat_id: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
    )


class DefaultTournamentChannel(Base):
    """Default Telegram destination for automatically discovered tournaments."""

    __tablename__ = "default_tournament_channel"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    chat_id: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
    )


class TopDeckWebhookEvent(Base):
    """Durable inbox for idempotent TopDeck webhook processing."""

    __tablename__ = "topdeck_webhook_events"

    event_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tournament_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
    )


class TournamentCompletionReview(Base):
    """Persist third-place confirmation and final tournament results."""

    __tablename__ = "tournament_completion_reviews"

    tournament_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    review_token: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
    )
    chat_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tournament_name: Mapped[str] = mapped_column(String(255), nullable=False)
    standings: Mapped[str] = mapped_column(Text, nullable=False)
    candidates: Mapped[str] = mapped_column(Text, nullable=False)
    undefeated_player_ids: Mapped[str] = mapped_column(Text, nullable=False)
    participant_count: Mapped[int] = mapped_column(Integer, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    third_place_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    result_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
    )


class Notification(Base):
    """Model for tracking notifications sent to Telegram groups."""
    
    __tablename__ = "notifications"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tournament_id = Column(String(100), ForeignKey("tournaments.tournament_id"), nullable=False)
    group_id = Column(String(255), nullable=False)  # Telegram group/channel ID
    
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.utcnow())
    
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    tournament = relationship("Tournament", back_populates="notifications")
