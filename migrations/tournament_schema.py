"""
Database migration for creating initial tables.
Run this with: python migrations/init.py

This is used for version-controlled database schema changes.
"""

import os
from pathlib import Path
from src.models.database_manager import DatabaseManager


def get_migration_url():
    """Get database URL from environment or default to SQLite."""
    from dotenv import load_dotenv
    
    load_dotenv()
    
    db_url = os.getenv("DB_URL", "sqlite:///./telegram_bot.db")
    return db_url


def main():
    """Initialize database schema from migration files."""
    print("=" * 50)
    print("Database Migration - Initial Schema Setup")
    print("=" * 50)
    
    db_url = get_migration_url()
    
    print(f"\nUsing database: {db_url}")
    
    # Check for existing tables
    from sqlalchemy import inspect
    
    engine = DatabaseManager(db_url).engine
    inspector = inspect(engine)
    table_names = [table.name for table in inspector.get_table_names()]
    
    if table_names:
        print(f"Existing tables: {', '.join(table_names)}")
        response = input("Drop and recreate all tables? (y/n): ")
        if response.lower() == 'y':
            from src.models.database import Base
            Base.metadata.drop_all(bind=engine)
            print("Tables dropped. Recreating...")
    
    # Create all tables
    db_manager = DatabaseManager(db_url, echo=True)
    db_manager.create_all()
    
    print("\n" + "=" * 50)
    print("✅ Migration complete!")
    print("=" * 50)
    print("\nTo verify schema, run:")
    print(f"   sqlite3 {db_url} '.tables'")


if __name__ == "__main__":
    main()
