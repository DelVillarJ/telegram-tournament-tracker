# Configuration schemas for Pydantic validation

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TournamentConfig(BaseModel):
    """Configuration for tournament tracking."""
    auto_notify: bool = Field(default=True)
    poll_interval_seconds: int = Field(default=60, ge=10, le=300)
    max_concurrent_requests: int = Field(default=5)
    
    model_config = {"json_schema_extra": {"title": "Tournament Configuration"}}


class NotificationConfig(BaseModel):
    """Configuration for notifications."""
    enabled: bool = Field(default=True)
    priority_levels: List[str] = Field(default=["low", "normal", "high"])
    reaction_on_high_priority: bool = Field(default=False)
    
    model_config = {"json_schema_extra": {"title": "Notification Configuration"}}


class CacheConfig(BaseModel):
    """Cache configuration."""
    enabled: bool = Field(default=False)
    ttl_seconds: int = Field(default=60)
    redis_url: Optional[str] = None
    
    model_config = {"json_schema_extra": {"title": "Cache Configuration"}}
