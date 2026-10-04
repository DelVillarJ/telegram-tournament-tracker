"""Data models for the Telegram bot."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Tournament(BaseModel):
    """Represents a TopDeck tournament."""
    id: str
    name: str = Field(..., description="Tournament name")
    status: str = Field(default="active", description="Tournament status: active, completed, etc.")
    participant_count: int = Field(default=0, description="Number of participants")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "tourney_123",
                    "name": "Summer Grand Prix",
                    "status": "active",
                    "participant_count": 50,
                    "start_time": "2026-10-01T10:00:00Z"
                }
            ]
        }
    }


class TournamentStatus(BaseModel):
    """Tournament status for notification purposes."""
    tournament_id: str
    name: str
    status: str
    completed_at: Optional[datetime] = None
    
    @property
    def is_complete(self) -> bool:
        """Check if tournament is complete."""
        return self.status.lower() in ["completed", "finished", "ended"]


class StandingsEntry(BaseModel):
    """A single player's standing entry."""
    rank: int
    display_name: str
    points: int = Field(default=0)
    wins: int = Field(default=0)
    matches_played: int = Field(default=0)


class StandingsResponse(BaseModel):
    """Complete standings response."""
    tournament_id: str
    tournament_name: str
    tournament_status: str
    entries: List[StandingsEntry] = []


class NotificationRequest(BaseModel):
    """Notification request model."""
    message: str
    target_group_ids: List[str] = Field(default=[])
    priority: str = Field(default="normal", description="low, normal, high")
    timestamp: datetime = Field(default_factory=datetime.now)


class TournamentStatusResponse(BaseModel):
    """API response for tournament status."""
    success: bool
    message: Optional[str] = None
    data: Optional[TournamentStatus] = None
    error: Optional[str] = None
