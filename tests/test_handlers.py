"""Unit tests for handlers."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from aiogram import types
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.types import F
from aiogram import Router

from src.handlers import router as handlers_router
from src.services.topdeck import TopDeckService


@pytest.fixture
def mock_message():
    """Create a mock message object."""
    return types.Message(
        message_id=1,
        chat=types.Chat(id=1, type="private"),
        from_user=types.User(id=12345, is_bot=False),
        text="/start"
    )


@pytest.fixture
def mock_topdeck_service():
    """Create a mock TopDeck service."""
    service = MagicMock()
    service.get_active_tournaments.return_value = [
        {"id": "t1", "name": "Summer Cup", "status": "active"},
    ]
    return service


class TestHandlers:
    """Test cases for bot handlers."""
    
    @pytest.mark.asyncio
    async def test_start_command(self, mock_message):
        """Test /start command handler."""
        # Mock the answer method
        mock_message.answer = MagicMock()
        
        await start_command(mock_message)
        
        mock_message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_status_command_success(self, mock_message, mock_topdeck_service):
        """Test /status command with successful response."""
        mock_message.answer = MagicMock()
        
        # Need to patch the dependencies properly
        with patch('src.handlers.topdeck_service', mock_topdeck_service):
            await status_command(mock_message, mock_topdeck_service)
            
            mock_message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_status_command_no_tournaments(self, mock_message, mock_topdeck_service):
        """Test /status when no tournaments exist."""
        mock_topdeck_service.get_active_tournaments.return_value = []
        mock_message.answer = MagicMock()
        
        await status_command(mock_message, mock_topdeck_service)
    
    @pytest.mark.asyncio
    async def test_points_command_success(self, mock_message, mock_topdeck_service):
        """Test /points command."""
        mock_standings = {
            "tournament_id": "t1",
            "entries": [
                {"display_name": "Player1", "points": 150},
            ]
        }
        mock_topdeck_service.get_standings.return_value = mock_standings
        
        mock_message.answer = MagicMock()
        
        await points_command(mock_message, mock_topdeck_service)
    
    @pytest.mark.asyncio
    async def test_help_command(self, mock_message):
        """Test /help command."""
        mock_message.answer = MagicMock()
        
        await help_command(mock_message)
        
        # Check that response contains help text
        response = mock_message.answer.call_args[0][0]
        assert "/start" in response
        assert "/status" in response
    
    @pytest.mark.asyncio
    async def test_callback_handler(self):
        """Test tournament callback handler."""
        mock_callback = MagicMock()
        
        # This would need proper fixture setup for callback queries
