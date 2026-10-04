"""Initialize the database schema."""

import asyncio
import logging

from src.models.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


def main():
    """Initialize database and create tables."""
    
    # Use SQLite by default (can be configured in .env)
    db_url = "sqlite:///./telegram_bot.db"
    
    print("Initializing database...")
    
    db_manager = DatabaseManager(url=db_url, echo=True)
    
    try:
        asyncio.run(db_manager.create_all())
        asyncio.run(db_manager.run_migrations())
        
        # Verify tables were created
        with db_manager.engine.connect() as conn:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in result.fetchall()]
            
            print(f"\n✅ Database initialized!")
            print(f"   Tables created: {', '.join(tables)}")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    finally:
        db_manager.close()
    
    print("   Database ready to use.")


if __name__ == "__main__":
    main()
