"""Unit tests for TopDeck service."""

import pytest
from unittest.mock import patch, MagicMock
import requests

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
        mock_response.json.return_value = {
            "tournaments": [
                {"id": "t1", "name": "Summer Cup", "status": "active"},
                {"id": "t2", "name": "Autumn Grand Prix", "status": "active"},
            ]
        }
        
        with patch('requests.get', return_value=mock_response):
            result = topdeck_service.get_active_tournaments()
            
            assert len(result) == 2
            assert result[0]["id"] == "t1"
    
    def test_get_active_tournaments_empty(self, topdeck_service):
        """Test when no tournaments are active."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tournaments": []}
        
        with patch('requests.get', return_value=mock_response):
            result = topdeck_service.get_active_tournaments()
            
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
            result = topdeck_service.get_standings("t1")
            
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
        """Test handling network exceptions."""
        with patch('requests.get', side_effect=requests.RequestException("Network error")):
            result = topdeck_service.get_active_tournaments()
            
            assert result is None
    
    def test_get_tournament_500_error(self, topdeck_service):
        """Test handling 500 server errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        
        with patch('requests.get', return_value=mock_response):
            result = topdeck_service.get_tournament_details("test")
            
            assert result is None
