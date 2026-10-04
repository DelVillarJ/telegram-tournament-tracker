"""
Logging configuration for the Telegram bot.
Sets up log formatters, handlers, and rotation.
"""

import logging
from pathlib import Path
from typing import Optional


def configure_logging(
    level: str = 'INFO',
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    log_file: Optional[str] = None,
    console: bool = True,
    file: bool = False
) -> logging.Logger:
    """
    Configure and return the bot logger.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR).
        format: Log message format string.
        log_file: Optional log file path.
        console: Whether to output to console.
        file: Whether to output to file.
    
    Returns:
        Configured logger object.
    """
    # Create or get root logger
    logger = logging.getLogger('telegram_bot')
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Remove existing handlers if any (for reconfiguration)
    logger.handlers.clear()
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        console_formatter = logging.Formatter(format)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file and file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


# Create default logger instance
logger = configure_logging()
