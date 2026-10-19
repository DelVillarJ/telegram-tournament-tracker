"""TopDeck API integration service."""

import asyncio
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from sqlalchemy import func

from src.models.database import BonusAdjustment, Standings, Tournament
from src.models.database_manager import DatabaseManager
from src.topdeck._api import TopDeckAPI

logger = logging.getLogger(__name__)


class TopDeckService:
    """Service for integrating with TopDeck API."""
    
    def __init__(
        self,
        api_key: str,
        api_url: str = "https://topdeck.gg/api",
        database_manager: Optional[DatabaseManager] = None,
    ):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.api_client = TopDeckAPI(api_key, api_url)
        self.database_manager = database_manager
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    async def get_active_tournaments(self) -> List[Dict[str, Any]]:
        """Get all active tournaments from TopDeck.
        
        Returns:
            List of tournaments belonging to the authenticated TopDeck account.
        """
        return await asyncio.to_thread(self.api_client.get_my_tournaments)
    
    def get_tournament_details(self, tournament_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific tournament.
        
        Args:
            tournament_id: TopDeck tournament identifier
            
        Returns:
            Tournament details dictionary or None on error
        """
        try:
            url = f"{self.api_url}/tournaments/{tournament_id}"
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get tournament {tournament_id}: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
    
    async def get_standings(self, tournament_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get standings for a tournament.
        
        Args:
            tournament_id: Optional tournament ID (defaults to latest active)
            
        Returns:
            Standings data dictionary or None on error
        """
        try:
            if tournament_id:
                url = f"{self.api_url}/tournaments/{tournament_id}/standings"
            else:
                tournaments = await self.get_active_tournaments()
                if not tournaments:
                    return None
                
                tournament_id = tournaments[0].get('TID') or tournaments[0].get('id')
                if not tournament_id:
                    logger.error("TopDeck account returned a tournament without an ID.")
                    return None
                url = f"{self.api_url}/tournaments/{tournament_id}/standings"
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get standings: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    async def get_league_standings(self, year: int = 2026) -> List[Dict[str, Any]]:
        """Get cumulative points standings for all imported tournaments in a year."""
        database_manager = self.database_manager
        if database_manager is None:
            raise RuntimeError("A database manager is required for league standings.")

        def query_standings() -> List[Dict[str, Any]]:
            with database_manager.get_session() as session:
                bonus_totals = (
                    session.query(
                        BonusAdjustment.player_id.label("player_id"),
                        func.sum(BonusAdjustment.points).label("bonus_points"),
                    )
                    .group_by(BonusAdjustment.player_id)
                    .subquery()
                )
                bonus_points = func.coalesce(
                    func.max(bonus_totals.c.bonus_points), 0
                )
                rows = (
                    session.query(
                        Standings.player_id,
                        func.max(Standings.player_name).label("player_name"),
                        func.sum(Standings.points).label("earned_points"),
                        func.sum(Standings.wins).label("wins"),
                        func.count(Standings.id).label("events_played"),
                        bonus_points.label("bonus_points"),
                    )
                    .join(Tournament, Tournament.tournament_id == Standings.tournament_id)
                    .outerjoin(
                        bonus_totals,
                        bonus_totals.c.player_id == Standings.player_id,
                    )
                    .filter(
                        Standings.player_id.isnot(None),
                        Tournament.start_time >= datetime(year, 1, 1),
                        Tournament.start_time < datetime(year + 1, 1, 1),
                    )
                    .group_by(Standings.player_id)
                    .order_by(
                        (
                            func.sum(Standings.points)
                            + bonus_points
                        ).desc(),
                        func.max(Standings.player_name).asc(),
                    )
                    .all()
                )
                return [
                    {
                        "player_id": row.player_id,
                        "player_name": row.player_name,
                        "points": (row.earned_points or 0) + row.bonus_points,
                        "bonus_points": row.bonus_points,
                        "wins": row.wins or 0,
                        "events_played": row.events_played,
                    }
                    for row in rows
                ]

        return await asyncio.to_thread(query_standings)

    async def add_bonus_points(
        self,
        player_identifier: str,
        points: int,
        *,
        added_by: str,
        year: int = 2026,
    ) -> Dict[str, Any]:
        """Append a signed bonus adjustment for a league player."""
        database_manager = self.database_manager
        if database_manager is None:
            raise RuntimeError("A database manager is required for bonus adjustments.")
        if not player_identifier.strip():
            raise ValueError("Provide a player name or TopDeck player ID.")
        if isinstance(points, bool) or not isinstance(points, int):
            raise ValueError("Bonus adjustment must be a whole number.")
        if points == 0:
            raise ValueError("Bonus adjustment must be a non-zero whole number.")

        identifier = player_identifier.strip()

        def save_adjustment() -> Dict[str, Any]:
            with database_manager.get_session() as session:
                with session.begin():
                    players = (
                        session.query(
                            Standings.player_id,
                            func.max(Standings.player_name).label("player_name"),
                        )
                        .join(
                            Tournament,
                            Tournament.tournament_id == Standings.tournament_id,
                        )
                        .filter(
                            Standings.player_id.isnot(None),
                            Tournament.start_time >= datetime(year, 1, 1),
                            Tournament.start_time < datetime(year + 1, 1, 1),
                        )
                        .group_by(Standings.player_id)
                        .all()
                    )
                    matching_players = [
                        player
                        for player in players
                        if player.player_id == identifier
                        or player.player_name.casefold() == identifier.casefold()
                    ]
                    if not matching_players:
                        raise ValueError(
                            f"No {year} league player matches {identifier!r}."
                        )
                    if len(matching_players) > 1:
                        raise ValueError(
                            f"More than one {year} league player matches that name; "
                            "use the TopDeck player ID instead."
                        )

                    player = matching_players[0]
                    session.add(
                        BonusAdjustment(
                            player_id=player.player_id,
                            player_name=player.player_name,
                            points=points,
                            added_by=added_by,
                        )
                    )
                    session.flush()
                    bonus_points = (
                        session.query(func.sum(BonusAdjustment.points))
                        .filter(BonusAdjustment.player_id == player.player_id)
                        .scalar()
                        or 0
                    )
                    earned_points = (
                        session.query(func.sum(Standings.points))
                        .join(
                            Tournament,
                            Tournament.tournament_id == Standings.tournament_id,
                        )
                        .filter(
                            Standings.player_id == player.player_id,
                            Tournament.start_time >= datetime(year, 1, 1),
                            Tournament.start_time < datetime(year + 1, 1, 1),
                        )
                        .scalar()
                        or 0
                    )
                    return {
                        "player_id": player.player_id,
                        "player_name": player.player_name,
                        "bonus_points": bonus_points,
                        "total_points": earned_points + bonus_points,
                    }

        return await asyncio.to_thread(save_adjustment)
    
    def check_tournament_status(self, tournament_id: str) -> Dict[str, Any]:
        """Check the current status of a tournament.
        
        Args:
            tournament_id: TopDeck tournament identifier
            
        Returns:
            Status information dictionary
        """
        try:
            details = self.get_tournament_details(tournament_id)
            
            if not details:
                return {
                    "status": "error",
                    "message": f"Tournament {tournament_id} not found"
                }
            
            status = {
                "status": "active",
                "name": details.get('name', ''),
                "participant_count": details.get('participant_count', 0),
                "max_participants": details.get('max_participants', None),
                "end_time": details.get('end_time')
            }
            
            # Check if tournament is about to end or completed
            if details.get('status') == 'completed':
                status["status"] = "completed"
                status["message"] = f"Tournament '{details['name']}' has been completed!"
                
            return status
            
        except Exception as e:
            logger.error(f"Error checking tournament status: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_participant_info(self, participant_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific participant.
        
        Args:
            participant_id: TopDeck participant identifier
            
        Returns:
            Participant info dictionary or None on error
        """
        try:
            url = f"{self.api_url}/participants/{participant_id}"
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get participant info: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def sync_tournament_data(self, tournament_id: str) -> bool:
        """Sync local tournament data with TopDeck API.
        
        Args:
            tournament_id: TopDeck tournament identifier
            
        Returns:
            True if sync successful, False otherwise
        """
        try:
            details = self.get_tournament_details(tournament_id)
            
            if not details:
                return False
            
            # Update local data with latest from API
            # (Implementation depends on your database structure)
            
            return True
            
        except Exception as e:
            logger.error(f"Sync failed for {tournament_id}: {e}")
            return False
