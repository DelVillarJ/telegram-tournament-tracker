"""Script to import historical tournament data from images/logs into the database."""

import asyncio
from datetime import datetime
from src.models.database_manager import DatabaseManager
from src.models.database import Tournament, Standings
from src.services.points_calculator import calculate_points

async def import_historical_data():
    # Initialize DB
    db_manager = DatabaseManager(url="sqlite:///C:\\Users\\jdelv\\Documents\\python\\telegrambot\\data\\tournaments.db")
    session = db_manager.get_session()
    
    # Data extracted from the provided image
    # Format: (Name, Position, Date, IsMonthly)
    historical_events = [
        ("Isaias Birthday Monthly", 3, "2026-07-18", True),
        ("Poyo Monthly", 4, "2026-07-09", True),
        ("World Cup Weekly pt2 @joses", 4, "2026-06-18", False),
        ("Poyo World Cup Weekly @Jose's", 2, "2026-06-18", False),
        ("World Cup monthly at Manny's brother house", 6, "2026-06-12", True),
        ("poyo weekly", 6, "2026-06-03", False),
        ("Poyo monthly", 3, "2026-05-24", True),
        ("Poyo weekly", 4, "2026-05-15", False),
        ("Poyo weekly", 1, "2026-05-15", False),
        ("Poyo weekly", 2, "2026-04-18", False),
        ("Poyo weekly", 2, "2026-04-06", False),
        ("Poyo Monthly", 2, "2026-04-04", True),
        ("poyo weekly", 1, "2026-03-07", False),
        ("poyo monthly", 8, "2026-03-07", True),
        ("poyo weekly", 1, "2026-02-28", False),
        ("poyo weekly", 4, "2026-02-28", False),
        ("poyo monthly", 3, "2026-02-20", True),
        ("poyo online weekly", 4, "2026-02-12", False),
        ("Poyo Online Weekly", 2, "2026-02-12", False),
        ("Poyo Weekly #4", 5, "2026-01-30", False),
        ("Poyo Weekly #3", 2, "2026-01-30", False),
        ("Jorge's HEB Freakoff", 1, "2026-01-24", False),
        ("Poyo Weekly 2", 5, "2026-01-02", False),
        ("Poyo Weekly 1", 1, "2026-01-02", False),
    ]
    
    print(f"Importing {len(historical_events)} events...")
    
    for name, pos, date_str, is_monthly in historical_events:
        # Create Tournament
        t_id = f"hist_{name.replace(' ', '_').lower()}_{date_str}"
        tournament = session.query(Tournament).filter_by(tournament_id=t_id).first()
        
        if not tournament:
            tournament = Tournament(
                name=name,
                tournament_id=t_id,
                status="completed",
                end_time=datetime.strptime(date_str, "%Y-%m-%d")
            )
            session.add(tournament)
            session.flush() # Get tournament_id
        
        # Calculate points
        pts = calculate_points(pos, is_monthly)
        
        # Create Standing (assuming a single target player for this import)
        standing = Standings(
            tournament_id=tournament.tournament_id,
            player_name="Target Player", # Replace with actual player name if known
            points=pts
        )
        session.add(standing)
        
    session.commit()
    session.close()
    print("Historical data import complete!")

if __name__ == "__main__":
    asyncio.run(import_historical_data())
