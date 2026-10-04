"""
TopDeck API integration module.
Provides functions to fetch tournaments, parse results, and handle API communication.
Uses SQLite for data persistence as specified.
"""

import logging
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
import time

# Import our custom configuration
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import config


logger = logging.getLogger(__name__)


class TopDeckError(Exception):
    """Custom exception for TopDeck API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(f"{message} (Status: {status_code})" if status_code else message)


class TopDeckClient:
    """
    Client for TopDeck API V2.
    
    Handles authentication, request making, and error handling.
    Uses SQLite for caching responses when enabled.
    """
    
    def __init__(self):
        """Initialize the TopDeck client."""
        self.api_url = config.topdeck_api_url
        self.client_id = config.topdeck_client_id
        self.client_secret = config.topdeck_client_secret
        self.poll_interval = config.poll_interval
        self.retries = config.api_call_retries
        self.timeout = config.api_call_timeout
        self.debug = config.debug
        
        # Cache for API responses (optional)
        if config.cache_enabled:
            from src.database import get_connection
            self._cache_conn = get_connection()
            self._cache_cursor = self._cache_conn.cursor()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        if self.client_id and self.client_secret:
            # OAuth2 Bearer token format (example - adjust based on actual TopDeck auth)
            # In production, implement proper OAuth2 flow
            pass
        
        return headers
    
    def _make_request(
        self,
        endpoint: str,
        method: str = 'GET',
        data: Optional[Dict] = None
    ) -> Response:
        """
        Make an API request to TopDeck.
        
        Args:
            endpoint: API endpoint path (e.g., /v2/tournaments)
            method: HTTP method (GET, POST, etc.)
            data: Request payload (for POST requests)
        
        Returns:
            Response object with status and data.
        
        Raises:
            TopDeckError: On API error or rate limit.
        """
        url = f"{self.api_url}{endpoint}"
        headers = self._get_headers()
        
        # Log request if debug enabled
        if self.debug:
            logger.debug(f"API Request: {method} {url}")
        
        try:
            # In production, use actual requests/httpx library calls
            # For now, simulate successful response structure
            
            time.sleep(1)  # Simulate network delay for demo
        
        except Exception as e:
            if hasattr(e, 'status_code'):
                raise TopDeckError(
                    f"API request failed: {e}",
                    status_code=e.status_code
                )
            else:
                raise TopDeckError(f"Network error: {e}")
        
        return Response(data=data, status=200)
    
    def _handle_rate_limit(self, retry_after: int) -> None:
        """Handle rate limit from API response."""
        logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
        time.sleep(retry_after)


class Response:
    """Represents an API response."""
    
    def __init__(self, data: Any = None, status: int = 200):
        self.data = data
        self.status = status
    
    @property
    def is_success(self) -> bool:
        """Check if response is successful (2xx status)."""
        return 200 <= self.status < 300


def get_tournaments_for_user(user_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch tournaments for specified users from TopDeck API.
    
    Args:
        user_ids: List of TopDeck user IDs to fetch tournaments for.
    
    Returns:
        List of tournament dictionaries with basic info.
    """
    client = TopDeckClient()
    tournaments = []
    
    for user_id in user_ids:
        try:
            response = client._make_request(f'/tournaments?user_id={user_id}')
            
            if response.is_success and response.data:
                # Convert list response to dict list
                if isinstance(response.data, list):
                    tournaments.extend(response.data)
                elif isinstance(response.data, dict):
                    tournaments.append(response.data)
        
        except TopDeckError as e:
            logger.error(f"Failed to fetch tournaments for user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching tournaments: {e}")
    
    return tournaments


def get_user_tournaments(user_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get all tournaments for a specific user.
    
    Args:
        user_id: TopDeck user ID.
        status_filter: Filter by status ('ongoing', 'completed', etc.)
    
    Returns:
        List of tournament dictionaries.
    """
    client = TopDeckClient()
    try:
        # Build endpoint with optional filter
        endpoint = f'/tournaments?user_id={user_id}'
        if status_filter:
            endpoint += f'&status={status_filter}'
        
        response = client._make_request(endpoint)
        
        if response.is_success and response.data:
            tournaments = response.data
            
            # Add metadata to each tournament
            for t in tournaments:
                t['fetched_from'] = 'api'
                t['user_id'] = user_id
            
            return tournaments
        else:
            return []
    
    except TopDeckError as e:
        logger.error(f"API error fetching {user_id} tournaments: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return []


def parse_tournament_data(tournament: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and enrich tournament data from TopDeck API response.
    
    Args:
        tournament: Raw tournament data from API.
    
    Returns:
        Enriched tournament dictionary with parsed fields.
    """
    if not isinstance(tournament, dict):
        return {}
    
    # Extract relevant fields
    parsed = {
        'topdeck_tournament_id': str(tournament.get('id', '')),
        'name': tournament.get('name', ''),
        'category': tournament.get('category', ''),
        'status': tournament.get('status', 'pending'),
        'start_date': _parse_timestamp(tournament.get('startTime') or tournament.get('startDate')),
        'end_date': _parse_timestamp(tournament.get('endTime') or tournament.get('endDate')),
        'host_user_id': str(tournament.get('userId', '')),
        'total_prize_pool': float(tournament.get('prizePool', 0)) if tournament.get('prizePool') else 0,
    }
    
    # Add optional fields if present
    if 'description' in tournament:
        parsed['description'] = tournament['description']
    if 'location' in tournament:
        parsed['location'] = tournament['location']
    if 'registration_deadline' in tournament:
        parsed['registration_deadline'] = _parse_timestamp(tournament['registration_deadline'])
    
    # Parse participants/team info if available
    teams = tournament.get('teams', [])
    if teams:
        parsed['teams'] = teams
    
    return parsed


def detect_tournament_started(tournament_data: Dict[str, Any]) -> bool:
    """
    Detect if a tournament has just started.
    
    Args:
        tournament_data: Tournament data from TopDeck API.
    
    Returns:
        True if tournament has started (status changed to 'ongoing').
    """
    if not isinstance(tournament_data, dict):
        return False
    
    return tournament_data.get('status') == 'ongoing' and \
           (not tournament_data.get('start_date') or 
            datetime.now() >= _parse_timestamp(tournament_data.get('start_date')))


def detect_tournament_completed(tournament_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict]]:
    """
    Detect if a tournament has completed and extract completion data.
    
    Args:
        tournament_data: Tournament data from TopDeck API.
    
    Returns:
        Tuple of (completed, result_data). Result data is None if not completed.
    """
    if not isinstance(tournament_data, dict):
        return False, None
    
    status = tournament_data.get('status', '')
    end_date = tournament_data.get('endTime') or tournament_data.get('endDate')
    
    # Check if completed
    is_completed = status == 'completed' and end_date
    
    if not is_completed:
        return False, None
    
    # Extract completion data
    result_data = {
        'total_participants': len(tournament_data.get('teams', [])),
        'winner_team': tournament_data.get('winnerTeam') or 
                      tournament_data.get('topTeam') or
                      tournament_data.get('champion'),
        'final_standings': tournament_data.get('standings', []),
        'notes': tournament_data.get('comment') or '',
    }
    
    return True, result_data


def detect_tournament_cancelled(tournament_data: Dict[str, Any]) -> bool:
    """
    Detect if a tournament has been cancelled.
    
    Args:
        tournament_data: Tournament data from TopDeck API.
    
    Returns:
        True if tournament status is 'cancelled'.
    """
    return tournament_data.get('status') == 'cancelled'


def _parse_timestamp(iso_string: Optional[str]) -> Optional[datetime]:
    """
    Parse ISO format timestamp to datetime object.
    
    Args:
        iso_string: ISO 8601 formatted timestamp string.
    
    Returns:
        datetime object or None if parsing failed.
    """
    if not iso_string:
        return None
    
    try:
        # Handle various ISO formats (with/without milliseconds, timezone)
        for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', 
                    '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S']:
            try:
                return datetime.strptime(iso_string.replace('Z', '+0000'), fmt.replace('Z', ''))
            except ValueError:
                continue
        
        # Try standard Python format
        return datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse timestamp {iso_string}: {e}")
        return None


def get_tournament_results(tournament_id: str) -> Optional[Dict[str, Any]]:
    """
    Get completed tournament results from TopDeck.
    
    Args:
        tournament_id: TopDeck tournament ID.
    
    Returns:
        Tournament result data or None if not available.
    """
    client = TopDeckClient()
    try:
        response = client._make_request(f'/tournaments/{tournament_id}/results')
        
        if response.is_success and response.data:
            return parse_tournament_data(response.data)
        return None
    
    except TopDeckError as e:
        logger.error(f"Failed to get results for tournament {tournament_id}: {e}")
        return None


def fetch_and_process_tournaments(user_ids: List[str]) -> Dict[str, Any]:
    """
    Fetch tournaments from API and process for event detection.
    
    Args:
        user_ids: List of user IDs to fetch tournaments for.
    
    Returns:
        Dictionary containing:
        - new_tournaments: List of newly detected tournaments
        - completed_tournaments: List of (tournament, result_data) tuples
        - cancelled_tournaments: List of cancelled tournament IDs
    
    Raises:
        TopDeckError: On API authentication failure.
    """
    client = TopDeckClient()
    
    all_tournaments = []
    for user_id in user_ids:
        tournaments = get_user_tournaments(user_id)
        all_tournaments.extend(tournaments)
    
    if not all_tournaments:
        return {
            'new_tournaments': [],
            'completed_tournaments': [],
            'cancelled_tournaments': [],
            'error': None
        }
    
    # Parse tournament data
    parsed = []
    for t in all_tournaments:
        try:
            parsed.append(parse_tournament_data(t))
        except Exception as e:
            logger.error(f"Failed to parse tournament {t.get('id')}: {e}")
            continue
    
    # Detect events
    new_started = []
    completed = []
    cancelled = []
    
    for t in parsed:
        # Check if just started
        is_ongoing = detect_tournament_started(t)
        
        # Check if completed
        finished, result_data = detect_tournament_completed(t)
        if finished:
            completed.append((t, result_data))
        elif not t.get('start_date') and is_ongoing:
            # Just started (has status ongoing but no start_date set yet)
            new_started.append(t['topdeck_tournament_id'])
        
        # Check if cancelled
        if detect_tournament_cancelled(t):
            cancelled.append(t['topdeck_tournament_id'])
    
    return {
        'new_tournaments': new_started,
        'completed_tournaments': completed,
        'cancelled_tournaments': cancelled,
        'error': None
    }


def check_rate_limit_headers(response: Response) -> bool:
    """
    Check if response indicates rate limiting.
    
    Args:
        response: API response to check.
    
    Returns:
        True if rate limited, False otherwise.
    """
    # In production, check response headers for rate limit info
    return response.status == 429 or \
           (hasattr(response, 'headers') and 
            response.headers.get('Retry-After', '').isdigit())
