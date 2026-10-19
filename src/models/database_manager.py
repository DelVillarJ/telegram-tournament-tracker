"""Database management for the bot."""

from sqlalchemy import create_engine, inspect, text
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
            from .database import Base  # noqa
            
            try:
                # Import models to ensure relationships are loaded
                from .database import (
                    Admin,
                    BonusAdjustment,
                    DefaultTournamentChannel,
                    Notification,
                    Standings,
                    TopDeckWebhookEvent,
                    Tournament,
                    TournamentChannel,
                    TournamentCompletionReview,
                )
                
                # Create all tables
                Base.metadata.create_all(bind=self.engine)

                standings_columns = {
                    column["name"]
                    for column in inspect(self.engine).get_columns("standings")
                }
                missing_standings_columns = {
                    "player_id": "VARCHAR(100)",
                    "position": "INTEGER",
                    "undefeated_bonus": "INTEGER NOT NULL DEFAULT 0",
                }
                for column_name, column_type in missing_standings_columns.items():
                    if column_name in standings_columns:
                        continue
                    with self.engine.begin() as migration_connection:
                        migration_connection.execute(
                            text(
                                f"ALTER TABLE standings ADD COLUMN "
                                f"{column_name} {column_type}"
                            )
                        )

                logger.info("Database tables created successfully")
            except Exception as e:
                logger.error(f"Failed to create tables: {e}")
                raise

    def initialize_admins(
        self,
        configured_ids: set[str],
        configured_usernames: set[str],
    ) -> tuple[set[str], set[str]]:
        """Seed configured admins once and return the persisted admin sets."""
        from .database import Admin

        with self.get_session() as session:
            admins = session.query(Admin).all()
            if not admins:
                identifiers = {
                    *(str(user_id) for user_id in configured_ids),
                    *(username.strip().lstrip("@").casefold()
                      for username in configured_usernames),
                }
                session.add_all(
                    Admin(identifier=identifier, added_by="configuration")
                    for identifier in identifiers
                )
                session.commit()
                admins = session.query(Admin).all()

            admin_ids = {
                str(admin.identifier)
                for admin in admins
                if admin.identifier.isdecimal()
            }
            admin_usernames = {
                str(admin.identifier)
                for admin in admins
                if not admin.identifier.isdecimal()
            }
            return admin_ids, admin_usernames

    def add_admin(self, identifier: str, added_by: str) -> bool:
        """Persist an admin identifier, returning False if it already exists."""
        from .database import Admin

        with self.get_session() as session:
            if session.get(Admin, identifier) is not None:
                return False
            session.add(Admin(identifier=identifier, added_by=added_by))
            session.commit()
            return True

    def remove_admin(self, identifier: str) -> bool:
        """Remove an admin unless doing so would leave the bot without admins."""
        from .database import Admin

        with self.get_session() as session:
            admin = session.get(Admin, identifier)
            if admin is None:
                return False
            if session.query(Admin).count() <= 1:
                raise ValueError("The last admin cannot be removed.")
            session.delete(admin)
            session.commit()
            return True
    
    async def drop_all(self):
        """Drop all tables in the database (use with caution!)."""
        with self.engine.connect() as conn:
            try:
                from .database import Base
                
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
