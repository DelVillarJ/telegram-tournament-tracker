"""Database management for the bot."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and migrations."""
    
    def __init__(self, url: str, echo: bool = False):
        self.url = url
        self.engine = create_engine(url, echo=echo)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        
    def get_session(self) -> Session:
        """Get a database session.
        
        Returns:
            Database session object
        """
        return self.SessionLocal()
    
    async def create_all(self):
        """Create all tables in the database."""
        with self.engine.connect() as conn:
            from .models.database import Base  # noqa
            
            try:
                # Import models to ensure relationships are loaded
                from .models.database import Tournament, Standings, Notification
                
                # Create all tables
                Base.metadata.create_all(bind=self.engine)
                
                logger.info("Database tables created successfully")
            except Exception as e:
                logger.error(f"Failed to create tables: {e}")
                raise
    
    async def drop_all(self):
        """Drop all tables in the database (use with caution!)."""
        with self.engine.connect() as conn:
            try:
                from .models.database import Base
                
                Base.metadata.drop_all(bind=self.engine)
                logger.info("All tables dropped")
            except Exception as e:
                logger.error(f"Failed to drop tables: {e}")
                raise
    
    async def run_migrations(self):
        """Run database migrations.
        
        For SQLite, this just creates the schema.
        For PostgreSQL, would apply migration files from migrations/ directory.
        """
        import os
        
        # Check if migration files exist
        migration_dir = "migrations"
        if os.path.exists(migration_dir):
            logger.info(f"Found migration directory: {migration_dir}")
            
            # In a production setup, you would:
            # 1. List available migrations
            # 2. Compare with current schema version
            # 3. Run pending migrations
            
            # For now, just create the schema if tables don't exist
            await self.create_all()
        else:
            logger.info("No migration directory found, using default schema")
    
    def close(self):
        """Close database connection."""
        self.engine.dispose()
