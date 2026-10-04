"""Unit tests for notification service."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.services.notification import NotificationService


@pytest.fixture
def mock_bot():
    """Create a mock bot instance."""
    return MagicMock()


@pytest.fixture
def notification_service(mock_bot):
    """Create a notification service with mocked bot."""
    return NotificationService(
        bot_token="test_token",
        bot_properties=MagicMock()
    )


@pytest.mark.asyncio
async def test_send_to_groups_success(notification_service, mock_bot):
    """Test sending message to multiple groups."""
    # Setup
    mock_bot.send_message = MagicMock(side_effect=[
        # First call for group1
        types.Message(message_id=1, chat=MagicMock(id=1)),
        # Second call for group2
        types.Message(message_id=2, chat=MagicMock(id=2)),
    ])
    
    # Mock bot instance
    notification_service.bot = mock_bot
    
    result = await notification_service.send_to_groups(
        "Test message",
        group_ids=["123456", "789012"]
    )
    
    # Should have sent to 2 groups successfully
    assert result is True


@pytest.mark.asyncio
async def test_notify_tournament_complete(notification_service, mock_bot):
    """Test notification for tournament completion."""
    mock_bot.send_message = MagicMock(return_value=MagicMock())
    notification_service.bot = mock_bot
    
    result = await notification_service.notify_tournament_complete(
        tournament_id="t1",
        name="Summer Cup",
        participant_count=50,
        end_time=datetime(2026, 10, 2, 18, 0)
    )
    
    assert result is True


@pytest.mark.asyncio
async def test_standings_update_notification(notification_service, mock_bot):
    """Test sending standings update notification."""
    top_5_players = [
        {"display_name": "Player1", "points": 150},
        {"display_name": "Player2", "points": 140},
        {"display_name": "Player3", "points": 135},
        {"display_name": "Player4", "points": 120},
        {"display_name": "Player5", "points": 110},
    ]
    
    mock_bot.send_message = MagicMock(return_value=MagicMock())
    notification_service.bot = mock_bot
    
    result = await notification_service.notify_standings_updated(
        tournament_id="t1",
        top_5_players=top_5_players
    )
    
    assert result is True


@pytest.mark.asyncio
async def test_send_to_groups_with_forbidden_chars(notification_service, mock_bot):
    """Test message with HTML characters uses correct parse mode."""
    html_message = "Use <b>bold</b> text"
    
    # This should handle forbidden chars correctly
    
    result = await notification_service.send_to_groups(html_message)
    
    # Should have been sent successfully
