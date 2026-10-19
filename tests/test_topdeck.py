"""Unit tests for TopDeck service."""

import asyncio
from datetime import datetime
import pytest
from unittest.mock import patch, MagicMock
import requests

from src.models.database import BonusAdjustment, Standings, Tournament
from src.models.database_manager import DatabaseManager
from src.services.topdeck import TopDeckService


@pytest.fixture
def topdeck_service():
    """Create a mock TopDeck service instance."""
    return TopDeckService(
        api_key="test_api_key_12345",
        api_url="https://api.test-topdeck.io/"
    )


class TestTopDeckService:
    """Test cases for TopDeckService class."""
    
    def test_get_active_tournaments_success(self, topdeck_service):
        """Test fetching active tournaments on success."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"TID": "t1", "tournamentName": "Summer Cup"},
            {"TID": "t2", "tournamentName": "Autumn Grand Prix"},
        ]
        
        with patch('requests.get', return_value=mock_response):
            result = asyncio.run(topdeck_service.get_active_tournaments())
            
            assert len(result) == 2
            assert result[0]["TID"] == "t1"
    
    def test_get_active_tournaments_empty(self, topdeck_service):
        """Test when no tournaments are active."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        
        with patch('requests.get', return_value=mock_response):
            result = asyncio.run(topdeck_service.get_active_tournaments())
            
            assert result == []
    
    def test_get_tournament_details_success(self, topdeck_service):
        """Test fetching single tournament details."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "t1",
            "name": "Summer Cup",
            "status": "active",
            "participant_count": 50,
            "start_time": "2026-10-01T10:00:00Z"
        }
        
        with patch('requests.get', return_value=mock_response):
            result = topdeck_service.get_tournament_details("t1")
            
            assert result["name"] == "Summer Cup"
    
    def test_get_standings_success(self, topdeck_service):
        """Test fetching standings data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tournament_id": "t1",
            "entries": [
                {"rank": 1, "display_name": "Player1", "points": 150},
                {"rank": 2, "display_name": "Player2", "points": 140},
            ]
        }
        
        with patch('requests.get', return_value=mock_response):
            result = asyncio.run(topdeck_service.get_standings("t1"))
            
            assert len(result["entries"]) == 2
    
    def test_get_tournament_not_found(self, topdeck_service):
        """Test when tournament doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Tournament not found"}
        
        with patch('requests.get', return_value=mock_response):
            result = topdeck_service.get_tournament_details("nonexistent")
            
            assert result is None
    
    def test_get_participant_info(self, topdeck_service):
        """Test fetching participant information."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "p1",
            "display_name": "Test Player",
            "current_tournaments": ["t1"]
        }
        
        with patch('requests.get', return_value=mock_response):
            result = topdeck_service.get_participant_info("p1")
            
            assert result["display_name"] == "Test Player"


class TestTopDeckServiceErrors:
    """Error handling tests for TopDeckService."""
    
    def test_get_tournaments_request_exception(self, topdeck_service):
        """Test that network exceptions from the TopDeck client propagate."""
        with patch('requests.get', side_effect=requests.RequestException("Network error")):
            with pytest.raises(requests.RequestException, match="Network error"):
                asyncio.run(topdeck_service.get_active_tournaments())
    
    def test_get_tournament_500_error(self, topdeck_service):
        """Test handling 500 server errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        
        with patch('requests.get', return_value=mock_response):
            result = topdeck_service.get_tournament_details("test")
            
            assert result is None


def test_get_league_standings_aggregates_points_for_requested_year(tmp_path):
    database_path = (tmp_path / "league.db").as_posix()
    database_manager = DatabaseManager(f"sqlite:///{database_path}")
    asyncio.run(database_manager.create_all())
    try:
        with database_manager.get_session() as session:
            with session.begin():
                session.add_all([
                    Tournament(
                        tournament_id="2026-weekly",
                        name="Weekly",
                        status="completed",
                        start_time=datetime(2026, 3, 1),
                    ),
                    Tournament(
                        tournament_id="2026-monthly",
                        name="Monthly",
                        status="completed",
                        start_time=datetime(2026, 4, 1),
                    ),
                    Tournament(
                        tournament_id="2025-weekly",
                        name="Old event",
                        status="completed",
                        start_time=datetime(2025, 12, 31),
                    ),
                ])
                session.add_all([
                    Standings(
                        tournament_id="2026-weekly",
                        player_id="player-1",
                        player_name="Player One",
                        position=1,
                        points=6,
                        wins=3,
                        matches_played=4,
                    ),
                    Standings(
                        tournament_id="2026-monthly",
                        player_id="player-1",
                        player_name="Player One",
                        position=1,
                        points=25,
                        wins=4,
                        matches_played=5,
                    ),
                    Standings(
                        tournament_id="2025-weekly",
                        player_id="player-1",
                        player_name="Player One",
                        position=1,
                        points=99,
                        wins=9,
                        matches_played=9,
                    ),
                    Standings(
                        tournament_id="2026-weekly",
                        player_id="player-2",
                        player_name="Player Two",
                        position=2,
                        points=4,
                        wins=2,
                        matches_played=4,
                    ),
                ])

        service = TopDeckService(
            "test_api_key_12345",
            database_manager=database_manager,
        )
        standings = asyncio.run(service.get_league_standings(year=2026))

        assert standings == [
            {
                "player_id": "player-1",
                "player_name": "Player One",
                "points": 31,
                "bonus_points": 0,
                "wins": 7,
                "events_played": 2,
            },
            {
                "player_id": "player-2",
                "player_name": "Player Two",
                "points": 4,
                "bonus_points": 0,
                "wins": 2,
                "events_played": 1,
            },
        ]
    finally:
        database_manager.close()


def test_bonus_adjustments_accumulate_and_apply_to_league_total(tmp_path):
    database_path = (tmp_path / "bonus-league.db").as_posix()
    database_manager = DatabaseManager(f"sqlite:///{database_path}")
    asyncio.run(database_manager.create_all())
    try:
        with database_manager.get_session() as session:
            with session.begin():
                session.add(
                    Tournament(
                        tournament_id="bonus-event",
                        name="League event",
                        status="completed",
                        start_time=datetime(2026, 3, 1),
                    )
                )
                session.add(
                    Standings(
                        tournament_id="bonus-event",
                        player_id="player-1",
                        player_name="Player One",
                        position=1,
                        points=6,
                        wins=3,
                        matches_played=4,
                    )
                )

        service = TopDeckService(
            "test_api_key_12345",
            database_manager=database_manager,
        )
        first_adjustment = asyncio.run(
            service.add_bonus_points("Player One", 5, added_by="admin-1")
        )
        second_adjustment = asyncio.run(
            service.add_bonus_points("player-1", -8, added_by="admin-1")
        )
        standings = asyncio.run(service.get_league_standings(year=2026))

        assert first_adjustment["bonus_points"] == 5
        assert first_adjustment["total_points"] == 11
        assert second_adjustment["bonus_points"] == -3
        assert second_adjustment["total_points"] == 3
        assert standings[0]["bonus_points"] == -3
        assert standings[0]["points"] == 3
        with database_manager.get_session() as session:
            assert session.query(BonusAdjustment).count() == 2
    finally:
        database_manager.close()


def test_bonus_adjustment_rejects_unknown_player(tmp_path):
    database_manager = DatabaseManager(
        f"sqlite:///{(tmp_path / 'unknown-player.db').as_posix()}"
    )
    asyncio.run(database_manager.create_all())
    try:
        service = TopDeckService(
            "test_api_key_12345",
            database_manager=database_manager,
        )

        with pytest.raises(ValueError, match="No 2026 league player matches"):
            asyncio.run(
                service.add_bonus_points("Nobody", 5, added_by="admin-1")
            )
    finally:
        database_manager.close()
