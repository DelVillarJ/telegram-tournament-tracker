"""Initialize the database schema."""

import asyncio
import logging
from sqlalchemy import text

from src.config import config as settings
from src.models.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


def main():
    """Initialize database and create tables."""

    print("Initializing database...")
    settings.ensure_db_directory()
    db_manager = DatabaseManager(
        url=settings.get_database_url(),
        echo=settings.debug,
    )

    try:
        asyncio.run(db_manager.run_migrations())

        with db_manager.engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result.fetchall()]
            
            print("\nDatabase initialized.")
            print(f"Tables created: {', '.join(tables)}")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    finally:
        db_manager.close()

    print("Database ready to use.")


if __name__ == "__main__":
    main()
