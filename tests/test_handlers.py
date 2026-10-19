"""Unit tests for handlers."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from aiogram import types, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram import Router

from src.handlers import router as handlers_router
from src.handlers import (
    bonus_command,
    help_command,
    points_command,
    start_command,
    status_command,
)
from src.services.topdeck import TopDeckService


@pytest.fixture
def mock_message():
    """Create a mock message object."""
    from datetime import datetime
    message = MagicMock(spec=types.Message)
    message.message_id = 1
    message.chat = types.Chat(id=1, type="private")
    message.from_user = types.User(id=12345, is_bot=False, first_name="TestUser")
    message.text = "/start"
    message.date = datetime.now()
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_topdeck_service():
    """Create a mock TopDeck service."""
    service = MagicMock(spec=TopDeckService)
    service.get_active_tournaments = AsyncMock(return_value=[
        {"id": "t1", "name": "Summer Cup", "status": "active"},
    ])
    service.get_league_standings = AsyncMock(return_value=[
        {"player_name": "Player1", "points": 150, "events_played": 3},
    ])
    service.get_tournament_details = AsyncMock(return_value={
        "id": "t1", "name": "Summer Cup", "status": "active", "participant_count": 10
    })
    return service


class TestHandlers:
    """Test cases for bot handlers."""
    
    @pytest.mark.asyncio
    async def test_start_command(self, mock_message):
        """Test /start command handler."""
        await start_command(mock_message)
        
        mock_message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_status_command_success(self, mock_message, mock_topdeck_service):
        """Test /status command with successful response."""
        # No need to patch src.handlers.topdeck_service if we pass it as an argument
        await status_command(mock_message, mock_topdeck_service)

        mock_message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_command_no_tournaments(self, mock_message, mock_topdeck_service):
        """Test /status when no tournaments exist."""
        mock_topdeck_service.get_active_tournaments.return_value = []

        await status_command(mock_message, mock_topdeck_service)

        mock_message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_points_command_success(self, mock_message, mock_topdeck_service):
        """Test /points command."""
        mock_standings = [
            {
                "player_name": f"Player{rank}",
                "points": 150 - rank,
                "events_played": 3,
            }
            for rank in range(1, 13)
        ]
        mock_topdeck_service.get_league_standings.return_value = mock_standings

        await points_command(mock_message, mock_topdeck_service)

        mock_message.answer.assert_called_once()
        response = mock_message.answer.call_args.args[0]
        assert "2026 Poyo League Standings" in response
        assert "Player12" in response

    @pytest.mark.asyncio
    async def test_bonus_command_requires_allowlisted_user(
        self, mock_message, mock_topdeck_service
    ):
        await bonus_command(mock_message, mock_topdeck_service, set(), set())

        assert "not authorized" in mock_message.answer.call_args.args[0]
        mock_topdeck_service.add_bonus_points.assert_not_called()

    @pytest.mark.asyncio
    async def test_bonus_command_applies_signed_adjustment(
        self, mock_message, mock_topdeck_service
    ):
        mock_message.text = "/bonus -3 Player One"
        mock_topdeck_service.add_bonus_points = AsyncMock(return_value={
            "player_name": "Player One",
            "bonus_points": -3,
            "total_points": 28,
        })

        await bonus_command(
            mock_message,
            mock_topdeck_service,
            {str(mock_message.from_user.id)},
            set(),
        )

        mock_topdeck_service.add_bonus_points.assert_awaited_once_with(
            "Player One",
            -3,
            added_by=str(mock_message.from_user.id),
        )
        assert "-3 points" in mock_message.answer.call_args.args[0]

    @pytest.mark.asyncio
    async def test_bonus_command_authorizes_configured_username(
        self, mock_message, mock_topdeck_service
    ):
        mock_message.text = "/bonus +1 Player One"
        mock_message.from_user = types.User(
            id=mock_message.from_user.id,
            is_bot=False,
            first_name="TestUser",
            username="HTB_Deliver",
        )
        mock_topdeck_service.add_bonus_points = AsyncMock(return_value={
            "player_name": "Player One",
            "bonus_points": 1,
            "total_points": 32,
        })

        await bonus_command(
            mock_message,
            mock_topdeck_service,
            set(),
            {"htb_deliver"},
        )

        mock_topdeck_service.add_bonus_points.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_help_command(self, mock_message):
        """Test /help command."""
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
