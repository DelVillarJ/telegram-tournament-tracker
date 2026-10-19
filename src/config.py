"""
Configuration loader for the Telegram bot.
Loads settings from .env file and environment variables using SQLite database.
"""

import os
from typing import List
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


class Config:
    """Configuration manager for the TopDeck Tournament Tracking Bot."""
    
    def __init__(self):
        """Initialize configuration with environment variables."""
        self._load_from_env()
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Telegram bot configuration
        self.bot_token = os.getenv('BOT_TOKEN', '')
        
        # TopDeck API configuration (using SQLite as specified)
        self.topdeck_api_url = os.getenv(
            'TOPDECK_API_URL', 
            'https://topdeck.gg/api'
        )
        self.topdeck_api_key = os.getenv('TOPDECK_API_KEY', '')
        self.topdeck_client_id = os.getenv('TOPDECK_CLIENT_ID', '')
        self.topdeck_client_secret = os.getenv('TOPDECK_CLIENT_SECRET', '')
        self.topdeck_webhook_secret = os.getenv('TOPDECK_WEBHOOK_SECRET', '')
        self.topdeck_default_chat_id = os.getenv(
            'TOPDECK_DEFAULT_CHAT_ID',
            '-1004340474920',
        )
        self.webhook_host = os.getenv('WEBHOOK_HOST', '0.0.0.0')
        self.webhook_port = int(os.getenv('WEBHOOK_PORT', '8080'))

        bonus_admin_ids = os.getenv('BONUS_ADMIN_IDS', '')
        self.bonus_admin_ids = {
            user_id.strip()
            for user_id in bonus_admin_ids.split(',')
            if user_id.strip()
        }
        bonus_admin_usernames = os.getenv('BONUS_ADMIN_USERNAMES', '')
        self.bonus_admin_usernames = {
            username.strip().lstrip('@').casefold()
            for username in bonus_admin_usernames.split(',')
            if username.strip().lstrip('@')
        } | {'poyotcg'}
        
        # Database configuration (SQLite only)
        self.db_path = os.getenv(
            'DATABASE_PATH',
            str(Path(__file__).parent.parent / 'data' / 'tournaments.db'),
        )
        self.use_sqlite = os.getenv('DB_USE_SQLITE', 'true').lower() == 'true'
        
        # Tournament tracking configuration
        target_users = os.getenv('TARGET_USER_ID', '')
        self.target_user_ids = target_users.split(',') if target_users else []
        self.poll_interval = int(os.getenv('TOPDECK_POLL_INTERVAL', '60'))
        
        # Bot behavior configuration
        self.notify_on_complete = os.getenv(
            'NOTIFY_ON_COMPLETE', 'true'
        ).lower() == 'true'
        self.auto_update_standings = os.getenv(
            'AUTO_UPDATE_STANDINGS', 'true'
        ).lower() == 'true'
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        
        # Performance & caching configuration
        self.cache_enabled = os.getenv(
            'CACHE_ENABLED', 'false'
        ).lower() == 'true'
        self.cache_ttl = int(os.getenv('CACHE_TTL', '60'))
        
        # Logging configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_format = os.getenv('LOG_FORMAT', 'plain')
        self.log_file = os.getenv('LOG_FILE')
        
        # Security configuration
        self.api_call_retries = int(os.getenv('API_CALL_RETRIES', '3'))
        self.api_call_timeout = int(os.getenv('API_CALL_TIMEOUT', '30'))
    
    @property
    def bot_token(self) -> str:
        """Get the Telegram bot token."""
        return self._bot_token
    
    @bot_token.setter
    def bot_token(self, value: str) -> None:
        """Set the Telegram bot token with validation."""
        if not value or len(value) < 15:
            raise ValueError("Invalid bot token. Must be at least 15 characters.")
        self._bot_token = value
    
    @property
    def db_path(self) -> Path:
        """Get the database path."""
        return Path(self._db_path)
    
    @db_path.setter
    def db_path(self, value: str) -> None:
        """Set the database path."""
        self._db_path = value
    
    def get_database_url(self) -> str:
        """Get the database URL for SQLAlchemy (SQLite only)."""
        if not self.use_sqlite:
            raise ValueError("This configuration only supports SQLite databases.")
        return f"sqlite:///{self.db_path}"
    
    def ensure_db_directory(self) -> None:
        """Ensure the database directory exists."""
        db_dir = Path(self._db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def get_target_user_ids(self) -> List[str]:
        """Get list of user IDs to track tournaments from."""
        return self.target_user_ids
    
    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.debug


# Create a singleton instance for easy import
config = Config()
