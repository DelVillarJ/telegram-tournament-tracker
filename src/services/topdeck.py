"""TopDeck API integration service."""

import requests
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TopDeckService:
    """Service for integrating with TopDeck API."""
    
    def __init__(self, api_key: str, api_url: str = "https://api.topdeck.io/"):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def get_active_tournaments(self) -> Optional[List[Dict[str, Any]]]:
        """Get all active tournaments from TopDeck.
        
        Returns:
            List of tournament dictionaries or None on error
        """
        try:
            url = f"{self.api_url}/tournaments"
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Filter for active tournaments
                return data.get('tournaments', [])[:10]  # Limit to first 10
            else:
                logger.error(f"Failed to get tournaments: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
    
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
    
    def get_standings(self, tournament_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
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
                # Get standings for latest active tournament
                tournaments = self.get_active_tournaments()
                if not tournaments:
                    return None
                
                # Find an active tournament
                for t in tournaments:
                    if t.get('status') == 'active':
                        tournament_id = t['id']
                        url = f"{self.api_url}/tournaments/{tournament_id}/standings"
                        break
            
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
