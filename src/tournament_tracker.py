"""
Tournament tracking and completion detection logic.
Handles polling, event detection, and database updates.
Uses SQLite as specified.
"""

import logging
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
import time

# Import our modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import config
from src.database import (
    get_active_tournaments,
    update_tournament_status,
    mark_tournament_completed,
    archive_tournament,
)
from src.topdeck_api import (
    fetch_and_process_tournaments,
    detect_tournament_started,
    detect_tournament_completed,
    detect_tournament_cancelled,
    TopDeckError,
)


logger = logging.getLogger(__name__)


class TournamentTracker:
    """
    Manages tournament tracking and event detection.
    
    Responsible for:
    - Periodic API polling
    - Detecting tournament events (start, complete, cancel)
    - Updating database with new data
    - Triggering notifications
    """
    
    def __init__(self):
        """Initialize the tournament tracker."""
        self.user_ids = config.get_target_user_ids()
        self.poll_interval = config.poll_interval
        self.debug = config.debug
        
        # Track last seen tournaments to detect changes
        self._last_seen_tournaments: Dict[str, Dict] = {}
        
        # Callbacks for events (can be customized)
        self._on_new_tournament: Optional[Callable] = None
        self._on_completion: Optional[Callable] = None
        self._on_cancellation: Optional[Callable] = None
    
    def set_callback(
        self,
        event_type: str,
        callback: Callable
    ) -> None:
        """
        Set a callback for a specific event type.
        
        Args:
            event_type: 'new', 'completion', or 'cancellation'
            callback: Function to call when event occurs
        """
        if event_type == 'new':
            self._on_new_tournament = callback
        elif event_type == 'completion':
            self._on_completion = callback
        elif event_type == 'cancellation':
            self._on_cancellation = callback
    
    def _notify_new_tournament(self, tournament_id: str) -> None:
        """Notify about new tournament (placeholder for point logic)."""
        if self._on_new_tournament:
            try:
                self._on_new_tournament(tournament_id)
            except Exception as e:
                logger.error(f"New tournament callback failed: {e}")
    
    def _notify_completion(
        self,
        tournament: Dict,
        result_data: Optional[Dict]
    ) -> None:
        """Notify about tournament completion."""
        if config.notify_on_complete and self._on_completion:
            try:
                self._on_completion(tournament, result_data)
            except Exception as e:
                logger.error(f"Completion callback failed: {e}")
        elif config.notify_on_complete:
            # Default notification message (placeholder for point logic)
            message = (
                f"🏆 *Tournament Completed!*\n\n"
                f"Name: {tournament.get('name', 'Unknown')}\n"
                f"Teams: {result_data.get('total_participants', 0) if result_data else 'N/A'}\n"
                f"Winner: {result_data.get('winner_team', 'TBD')} (pending point calculation)\n\n"
                "*Standings will be updated shortly.*"
            )
            logger.info(f"Notification would be sent: {message}")
    
    def _notify_cancellation(self, tournament_id: str) -> None:
        """Notify about cancelled tournament."""
        if self._on_cancellation:
            try:
                self._on_cancellation(tournament_id)
            except Exception as e:
                logger.error(f"Cancellation callback failed: {e}")
    
    def _update_tournament_in_db(self, tournament: Dict[str, Any]) -> None:
        """Update tournament in database with latest data."""
        try:
            topdeck_id = tournament.get('topdeck_tournament_id')
            name = tournament.get('name', '')
            category = tournament.get('category', '')
            status = tournament.get('status', 'ongoing')
            start_date = tournament.get('start_date')
            end_date = tournament.get('end_date')
            
            create_or_update_tournament(
                topdeck_id=topdeck_id,
                name=name,
                category=category,
                start_date=start_date,
                end_date=end_date,
                status=status
            )
            
        except Exception as e:
            logger.error(f"Failed to update tournament {topdeck_id}: {e}")
    
    def run_polling_loop(self) -> None:
        """
        Run the main polling loop.
        
        Continuously polls the TopDeck API for updates.
        """
        logger.info(f"Starting tournament tracking (interval: {self.poll_interval}s)")
        
        while True:
            try:
                # Fetch tournaments from API
                self._fetch_tournaments()
                
            except TopDeckError as e:
                logger.error(f"API error: {e}")
            
            except Exception as e:
                logger.error(f"Unexpected error in polling loop: {e}")
            
            finally:
                # Wait for next poll interval
                if self.poll_interval > 0:
                    time.sleep(self.poll_interval)
    
    def _fetch_tournaments(self) -> None:
        """Fetch tournaments from API and process updates."""
        logger.debug(f"Fetching tournaments for users: {self.user_ids}")
        
        # Fetch from TopDeck API
        results = fetch_and_process_tournaments(self.user_ids)
        
        if not results['new_tournaments'] and not results['completed_tournaments']:
            return
        
        # Update each tournament in database
        for tourney_id in results['new_tournaments']:
            self._update_tournament_in_db(tourney_id)
        
        # Process completed tournaments
        for tournament, result_data in results['completed_tournaments']:
            # Mark as completed in database
            mark_tournament_completed(
                int(tournament.get('topdeck_tournament_id')),
                {
                    'total_participants': result_data.get('total_participants'),
                    'winner_team': result_data.get('winner_team'),
                }
            )
            
            # Archive tournament
            archive_tournament(int(tournament.get('topdeck_tournament_id')))
            
            # Notify completion and handle point updates (placeholder for point logic)
            self._notify_completion(tournament, result_data)
        
        # Handle cancelled tournaments
        for tourney_id in results['cancelled_tournaments']:
            logger.warning(f"Tournament {tourney_id} was cancelled")
    
    def process_single_poll(self) -> Dict[str, List]:
        """
        Perform a single API poll and return detected events.
        
        Returns:
            Dictionary with lists of new, completed, and cancelled tournaments.
        """
        results = fetch_and_process_tournaments(self.user_ids)
        
        # Update database for each detected event
        for tourney_id in results['new_tournaments']:
            self._update_tournament_in_db(tourney_id)
            self._notify_new_tournament(tourney_id)
        
        for tournament, result_data in results['completed_tournaments']:
            mark_tournament_completed(
                int(tournament.get('topdeck_tournament_id')),
                {'total_participants': result_data.get('total_participants'), 'winner_team': result_data.get('winner_team')}
            )
            
            # Archive and notify (placeholder for point logic)
            archive_tournament(int(tournament.get('topdeck_tournament_id')))
            self._notify_completion(tournament, result_data)
        
        for tourney_id in results['cancelled_tournaments']:
            logger.warning(f"Tournament {tourney_id} was cancelled")
            if self._on_cancellation:
                self._on_cancellation(tourney_id)
        
        return results


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
    Create or update tournament in database.
    
    This function exists here for convenience (placeholder for point logic).
    """
    from src.database import create_or_update_tournament as _create
    
    return _create(
        topdeck_id=topdeck_id,
        name=name,
        category=category,
        start_date=start_date,
        end_date=end_date,
        host_user_id=host_user_id,
        status=status
    )


def archive_tournament(tournament_id: int) -> bool:
    """
    Archive a tournament (soft delete).
    
    Placeholder for point logic.
    """
    from src.database import archive_tournament as _archive
    
    return _archive(tournament_id)
