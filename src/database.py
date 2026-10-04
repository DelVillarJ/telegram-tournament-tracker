"""
Database schema and operations for SQLite persistence.
Provides functions to initialize tables, query data, and manage tournaments.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


def get_db_path() -> Path:
    """Get the database path."""
    return Path(__file__).parent.parent / 'data' / 'tournaments.db'


def get_connection() -> sqlite3.Connection:
    """
    Get a SQLite database connection.
    
    Returns:
        sqlite3.Connection: Database connection object.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def init_database() -> None:
    """
    Initialize the database and create all required tables.
    
    Creates tables for:
    - tournaments: Track tournament metadata and status
    - players: Player/team info per tournament
    - standings: Current standings with points, wins, losses
    - history_archive: Historical tournament data
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create tournaments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topdeck_tournament_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            status TEXT DEFAULT 'pending',
            host_user_id TEXT,
            total_prize_pool REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create players table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_chat_id INTEGER NOT NULL,
            tournament_id INTEGER REFERENCES tournaments(id) ON DELETE CASCADE,
            player_name TEXT NOT NULL,
            team TEXT,
            rank INTEGER,
            points INTEGER DEFAULT 0,
            UNIQUE(telegram_chat_id, tournament_id)
        )
    ''')
    
    # Create standings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER REFERENCES tournaments(id) ON DELETE CASCADE,
            position INTEGER NOT NULL,
            team_name TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            goal_for INTEGER DEFAULT 0,
            goal_against INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create history archive table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER UNIQUE REFERENCES tournaments(id) ON DELETE CASCADE,
            completion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_participants INTEGER,
            winner_team TEXT,
            final_standings TEXT,
            notes TEXT
        )
    ''')
    
    # Create index for faster lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tournaments_status 
        ON tournaments(status)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_standings_tournament
        ON standings(tournament_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_players_tournament
        ON players(tournament_id)
    ''')
    
    conn.commit()
    conn.close()


def create_or_update_tournament(
    topdeck_id: str,
    name: str,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    host_user_id: Optional[str] = None,
    status: str = 'pending'
) -> Dict[str, Any]:
    """
    Create a new tournament or update an existing one.
    
    Args:
        topdeck_id: TopDeck tournament ID (unique identifier)
        name: Tournament name
        category: Tournament category (optional)
        start_date: Start timestamp (ISO format or None for not started)
        end_date: End timestamp (ISO format or None for ongoing)
        host_user_id: Host user's ID
        status: Tournament status (pending, ongoing, completed, cancelled)
    
    Returns:
        Dictionary with tournament data and new ID if created.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if tournament exists
    cursor.execute('''
        SELECT id FROM tournaments 
        WHERE topdeck_tournament_id = ?
    ''', (topdeck_id,))
    
    existing = cursor.fetchone()
    
    if existing:
        # Update existing tournament
        cursor.execute('''
            UPDATE tournaments SET
                name = ?,
                category = ?,
                start_date = ?,
                end_date = ?,
                host_user_id = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE topdeck_tournament_id = ?
        ''', (name, category, start_date, end_date, host_user_id, status, topdeck_id))
        result = {'id': existing[0], 'status': 'updated'}
    else:
        # Insert new tournament
        cursor.execute('''
            INSERT INTO tournaments (
                topdeck_tournament_id, name, category, 
                start_date, end_date, host_user_id, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (topdeck_id, name, category, start_date, end_date, host_user_id, status))
        result = {'id': cursor.lastrowid, 'status': 'created'}
    
    conn.commit()
    conn.close()
    
    return result


def get_active_tournaments(host_user_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Get all active tournaments (ongoing or pending).
    
    Args:
        host_user_ids: Filter by host user IDs (optional)
    
    Returns:
        List of tournament dictionaries.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if host_user_ids:
        placeholders = ','.join(['?' for _ in host_user_ids])
        query = f'''
            SELECT t.* FROM tournaments t
            WHERE t.status IN ('ongoing', 'pending')
            AND t.host_user_id IN ({placeholders})
            ORDER BY t.start_date DESC
        '''
        cursor.execute(query, host_user_ids)
    else:
        query = '''
            SELECT * FROM tournaments
            WHERE status IN ('ongoing', 'pending')
            ORDER BY start_date DESC
        '''
        cursor.execute(query)
    
    columns = [description[0] for description in cursor.description]
    results = []
    for row in cursor.fetchall():
        results.append(dict(zip(columns, row)))
    
    conn.close()
    return results


def get_tournament_by_id(tournament_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a tournament by its database ID.
    
    Args:
        tournament_id: The database ID of the tournament.
    
    Returns:
        Tournament dictionary or None if not found.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tournaments WHERE id = ?', (tournament_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, row))
    return None


def mark_tournament_completed(
    tournament_id: int,
    completion_data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Mark a tournament as completed and optionally update related data.
    
    Args:
        tournament_id: Database ID of the tournament.
        completion_data: Optional completion details (results, participants, etc.)
    
    Returns:
        True if successful, False otherwise.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE tournaments SET
            status = 'completed',
            end_date = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND status != 'completed'
    ''', (tournament_id,))
    
    rows_affected = cursor.rowcount
    
    # If completion_data provided, store in history archive
    if completion_data:
        cursor.execute('''
            INSERT OR REPLACE INTO history_archive 
            (tournament_id, total_participants, winner_team, final_standings, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            tournament_id,
            completion_data.get('total_participants'),
            completion_data.get('winner_team'),
            completion_data.get('final_standings'),
            completion_data.get('notes', '')
        ))
    
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    
    return success


def archive_tournament(tournament_id: int) -> bool:
    """
    Archive a completed tournament (move to history).
    
    Args:
        tournament_id: Database ID of the tournament.
    
    Returns:
        True if successful, False if already archived or not found.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT status FROM tournaments WHERE id = ?
    ''', (tournament_id,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    
    if row[0] != 'completed':
        conn.close()
        return False
    
    cursor.execute('''
        INSERT OR REPLACE INTO history_archive 
        (tournament_id) VALUES (?)
    ''', (tournament_id,))
    
    cursor.execute('''
        UPDATE tournaments SET status = 'archived' WHERE id = ?
    ''', (tournament_id,))
    
    conn.commit()
    conn.close()
    
    return True


def update_tournament_status(
    topdeck_id: str,
    status: str
) -> bool:
    """
    Update tournament status based on TopDeck API data.
    
    Args:
        topdeck_id: TopDeck tournament ID.
        status: New status (ongoing, completed, cancelled).
    
    Returns:
        True if updated, False if not found.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE tournaments SET
            status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE topdeck_tournament_id = ? AND status != ?
    ''', (status, topdeck_id, status))
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return rows_affected > 0


def add_player(
    telegram_chat_id: int,
    tournament_id: int,
    player_name: str,
    team: Optional[str] = None,
    rank: Optional[int] = None
) -> bool:
    """
    Add a player to a tournament.
    
    Args:
        telegram_chat_id: Telegram chat/group ID.
        tournament_id: Tournament database ID.
        player_name: Player's display name.
        team: Team name (optional).
        rank: Player's rank (optional).
    
    Returns:
        True if added successfully, False if already exists or invalid tournament.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO players 
            (telegram_chat_id, tournament_id, player_name, team, rank)
            VALUES (?, ?, ?, ?, ?)
        ''', (telegram_chat_id, tournament_id, player_name, team, rank))
        
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result
    except sqlite3.IntegrityError:
        conn.close()
        return False


def get_standings_for_tournament(
    tournament_id: int,
    chat_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get standings for a specific tournament.
    
    Args:
        tournament_id: Tournament database ID.
        chat_id: Telegram chat ID to filter by (optional).
    
    Returns:
        List of standing dictionaries.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if chat_id:
        query = '''
            SELECT s.* FROM standings s
            JOIN players p ON s.tournament_id = p.tournament_id
            WHERE s.tournament_id = ? AND p.telegram_chat_id = ?
            ORDER BY s.position ASC
        '''
        cursor.execute(query, (tournament_id, chat_id))
    else:
        query = '''
            SELECT * FROM standings
            WHERE tournament_id = ?
            ORDER BY position ASC
        '''
        cursor.execute(query, (tournament_id,))
    
    columns = [description[0] for description in cursor.description]
    results = []
    for row in cursor.fetchall():
        results.append(dict(zip(columns, row)))
    
    conn.close()
    return results


def update_standings(
    tournament_id: int,
    standings_data: List[Dict[str, Any]]
) -> bool:
    """
    Update standings with new data.
    
    Args:
        tournament_id: Tournament database ID.
        standings_data: List of standings dictionaries.
    
    Returns:
        True if successful.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    for standing in standings_data:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO standings 
                (tournament_id, position, team_name, points, games_played,
                 wins, losses, draws, goal_for, goal_against)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                tournament_id,
                standing['position'],
                standing['team_name'],
                standing.get('points', 0),
                standing.get('games_played', 0),
                standing.get('wins', 0),
                standing.get('losses', 0),
                standing.get('draws', 0),
                standing.get('goal_for', 0),
                standing.get('goal_against', 0)
            ))
        except sqlite3.IntegrityError:
            # Handle duplicate entries gracefully
            pass
    
    conn.commit()
    conn.close()
    return True
