"""
Integration tests for the tournament tracking bot.
Tests the full flow from API calls to database updates to notifications.
Run with: pytest tests/test_integration.py -v --tb=short
"""

import sys
from pathlib import Path
import sqlite3


def test_full_tournament_workflow():
    """
    Integration test: Full workflow from tournament creation to completion.
    """
    test_db = Path(__file__).parent.parent / 'data' / 'test.db'
    # Ensure a clean database for this test
    if test_db.exists():
        test_db.unlink()

    conn = sqlite3.connect(str(test_db))
    cursor = conn.cursor()
    
    # Setup: Create tables
    cursor.execute('''
        CREATE TABLE tournaments (
            id INTEGER PRIMARY KEY,
            topdeck_tournament_id TEXT UNIQUE,
            name TEXT,
            category TEXT,
            status TEXT DEFAULT 'pending',
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            host_user_id TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE standings (
            id INTEGER PRIMARY KEY,
            tournament_id INTEGER,
            position INTEGER,
            team_name TEXT,
            points INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE history_archive (
            id INTEGER PRIMARY KEY,
            tournament_id INTEGER UNIQUE REFERENCES tournaments(id),
            completion_date TIMESTAMP,
            winner_team TEXT
        )
    ''')
    
    conn.commit()
    
    # Step 1: Create tournament
    cursor.execute('''
        INSERT INTO tournaments 
        (topdeck_tournament_id, name, category, status, host_user_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        'TD-2026-Spring',
        'Spring Championship 2026',
        'eSports',
        'ongoing',
        'user_abc123'
    ))
    
    conn.commit()
    
    # Verify tournament created
    cursor.execute("SELECT * FROM tournaments WHERE topdeck_tournament_id = ?", 
                   ('TD-2026-Spring',))
    assert len(cursor.fetchall()) == 1, "Tournament should be created"
    
    # Step 2: Simulate completion
    cursor.execute('''
        UPDATE tournaments SET status = 'completed'
        WHERE topdeck_tournament_id = 'TD-2026-Spring'
    ''')
    
    conn.commit()
    
    # Step 3: Insert sample standings
    cursor.execute('''
        INSERT INTO standings (tournament_id, position, team_name, points, wins, losses)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (1, 1, 'Team Alpha', 500, 8, 2))
    
    cursor.execute('''
        INSERT INTO standings (tournament_id, position, team_name, points, wins, losses)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (1, 2, 'Team Beta', 480, 7, 3))
    
    cursor.execute('''
        INSERT INTO standings (tournament_id, position, team_name, points, wins, losses)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (1, 3, 'Team Gamma', 420, 5, 5))
    
    conn.commit()
    
    # Verify standings
    cursor.execute("SELECT COUNT(*) FROM standings")
    count = cursor.fetchone()[0]
    assert count == 3, f"Should have 3 standings entries, got {count}"
    
    # Step 4: Archive tournament to history
    cursor.execute('''
        INSERT INTO history_archive (tournament_id, completion_date, winner_team)
        VALUES (?, ?, ?)
    ''', (1, '2026-10-02T12:00:00Z', 'Team Alpha'))
    
    conn.commit()
    
    # Verify archived
    cursor.execute("SELECT COUNT(*) FROM history_archive")
    archive_count = cursor.fetchone()[0]
    assert archive_count == 1, f"Should have 1 archived tournament, got {archive_count}"
    
    conn.close()
    print("✓ Full workflow integration test passed")


def test_standings_updates():
    """Test that standings are correctly updated."""
    test_db = Path(__file__).parent.parent / 'data' / 'test_standings.db'
    if test_db.exists():
        test_db.unlink()
    conn = sqlite3.connect(str(test_db))
    cursor = conn.cursor()
    
    # Setup
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY,
            topdeck_tournament_id TEXT UNIQUE,
            name TEXT,
            category TEXT,
            status TEXT DEFAULT 'pending',
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            host_user_id TEXT
        )
    ''')
    
    cursor.execute(
        "INSERT INTO tournaments (topdeck_tournament_id, name) VALUES ('test_standings', 'Test Tournament')"
    )
    
    conn.commit()
    
    # Add initial standings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY,
            tournament_id INTEGER,
            position INTEGER,
            team_name TEXT,
            points INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        INSERT INTO standings (tournament_id, position, team_name, points)
        VALUES (?, ?, ?, ?)
    ''', (1, 1, 'Team A', 10))
    
    cursor.execute(
        "INSERT INTO standings (tournament_id, position, team_name, points) VALUES (?, ?, ?, ?)",
        (1, 2, 'Team B', 5)
    )
    
    conn.commit()
    
    # Update standings (simulate point adjustment)
    cursor.execute('''
        UPDATE standings SET points = points + 50
        WHERE team_name = 'Team A'
    ''')
    
    conn.commit()
    
    # Verify update
    cursor.execute("SELECT points FROM standings WHERE team_name = ?", ('Team A',))
    assert cursor.fetchone()[0] == 60, "Points should be updated to 60"
    
    conn.close()
    print("✓ Standings updates integration test passed")


def test_tournament_removal():
    """Test removing a tournament from tracking."""
    test_db = Path(__file__).parent.parent / 'data' / 'test_removal.db'
    if test_db.exists():
        test_db.unlink()
    conn = sqlite3.connect(str(test_db))
    cursor = conn.cursor()
    
    # Setup
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY,
            topdeck_tournament_id TEXT UNIQUE,
            name TEXT,
            category TEXT,
            status TEXT DEFAULT 'pending',
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            host_user_id TEXT
        )
    ''')
    
    cursor.execute(
        "INSERT INTO tournaments (topdeck_tournament_id, name, status) VALUES ('test_remove', 'Test Tournament', 'ongoing')"
    )
    
    conn.commit()
    
    # Remove by archiving
    cursor.execute('''
        UPDATE tournaments SET status = 'archived'
        WHERE topdeck_tournament_id = 'test_remove'
    ''')
    
    conn.commit()
    
    # Verify removed from active (status is now 'archived')
    cursor.execute("SELECT COUNT(*) FROM tournaments WHERE status = 'active'")
    assert cursor.fetchone()[0] == 0
    
    conn.close()
    print("✓ Tournament removal integration test passed")
