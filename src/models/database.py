"""Database models for storing tournament data and notifications."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid


Base = declarative_base()


class Tournament(Base):
    """Model for tracking TopDeck tournaments."""
    
    __tablename__ = "tournaments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tournament_id = Column(String(100), unique=True, nullable=False)  # TopDeck tournament ID
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="active")  # active, completed, etc.
    
    participant_count = Column(Integer, default=0)
    max_participants = Column(Integer, nullable=True)
    
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    is_notified = Column(Boolean, default=False)  # Has this tournament been notified?
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.utcnow())
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.utcnow())
    
    # Relationships
    notifications = relationship("Notification", back_populates="tournament", cascade="all, delete-orphan")
    standings = relationship("Standings", back_populates="tournament", cascade="all, delete-orphan")
    
    def is_complete(self):
        """Check if tournament is complete."""
        return self.status.lower() in ["completed", "finished", "ended"]


class Standings(Base):
    """Model for tournament standings/leaderboard."""
    
    __tablename__ = "standings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tournament_id = Column(String(100), ForeignKey("tournaments.tournament_id"), nullable=False)
    player_name = Column(String(100), nullable=False)
    points = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    matches_played = Column(Integer, default=0)
    
    # Relationships
    tournament = relationship("Tournament", back_populates="standings")


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
