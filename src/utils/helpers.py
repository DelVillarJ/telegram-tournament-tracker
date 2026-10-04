"""Utility functions for the bot."""

import logging
from typing import Optional


def setup_logger(
    name: str, 
    level: int = logging.INFO, 
    log_file: Optional[str] = None
) -> logging.Logger:
    """Setup a logger with console and optional file handlers.
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (default INFO)
        log_file: Optional path to log file
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if level == logging.DEBUG else level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to maximum length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text with '...' suffix if truncated
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'


def format_points(points: int) -> str:
    """Format points with emoji.
    
    Args:
        points: Number of points
        
    Returns:
        Formatted string (e.g., "🥇 Gold!", "🥈 Silver!")
    """
    if points >= 100:
        return f"🥇 {points} - Gold!"
    elif points >= 50:
        return f"🥈 {points} - Silver!"
    elif points >= 25:
        return f"🥉 {points} - Bronze!"
    else:
        return f"{points} pts"


def format_datetime(dt) -> str:
    """Format datetime for display.
    
    Args:
        dt: datetime object or string
        
    Returns:
        Formatted datetime string (e.g., "Oct 2, 2026 at 10:30 AM")
    """
    from datetime import datetime
    
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
    
    now = datetime.utcnow()
    if dt.year == now.year and dt.month == now.month and dt.day == now.day:
        return dt.strftime("%I:%M %p")  # Today: "10:30 AM"
    elif dt.year == now.year:
        return dt.strftime("%b %d, %Y at %I:%M %p")  # This month
    else:
        return dt.strftime("%b %d, %Y")  # Other months


def safe_get(data: dict, key: str, default=None) -> any:
    """Safely get a value from nested dictionary.
    
    Args:
        data: Dictionary to get from
        key: Key to look up (supports dot notation for nesting)
        default: Default value if key not found
        
    Returns:
        Value or default
    """
    keys = key.split('.') if isinstance(key, str) else [key]
    
    try:
        for k in keys:
            data = data[k]
        return data
    except (KeyError, TypeError):
        return default


def is_active_tournament(status: str) -> bool:
    """Check if tournament status indicates it's active.
    
    Args:
        status: Tournament status string
        
    Returns:
        True if tournament is active/ongoing
    """
    return status.lower() in ["active", "scheduled", "in_progress"]
