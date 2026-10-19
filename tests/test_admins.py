"""Tests for persistent Telegram admin management."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram import Dispatcher, types

from src.handlers import admin_command, set_default_channel_command, setup_handlers
from src.models.database import DefaultTournamentChannel
from src.models.database_manager import DatabaseManager


@pytest.mark.asyncio
async def test_admin_command_adds_and_removes_username(tmp_path):
    database_manager = DatabaseManager(f"sqlite:///{tmp_path / 'admins.db'}")
    await database_manager.create_all()
    admin_ids, admin_usernames = database_manager.initialize_admins(
        {str(12345)},
        {"poyotcg"},
    )
    message = MagicMock(spec=types.Message)
    message.from_user = types.User(
        id=12345,
        is_bot=False,
        first_name="Admin",
        username="PoyoTCG",
    )
    message.answer = AsyncMock()
    message.text = "/admin add @NewAdmin"

    await admin_command(
        message,
        database_manager,
        admin_ids,
        admin_usernames,
    )

    assert "newadmin" in admin_usernames
    message.answer.assert_awaited_with("✅ Added @NewAdmin as an admin.")

    message.text = "/admin remove newadmin"
    await admin_command(
        message,
        database_manager,
        admin_ids,
        admin_usernames,
    )

    assert "newadmin" not in admin_usernames
    message.answer.assert_awaited_with("✅ Removed newadmin as an admin.")
    database_manager.close()


@pytest.mark.asyncio
async def test_admin_command_rejects_unauthorized_user(tmp_path):
    database_manager = DatabaseManager(f"sqlite:///{tmp_path / 'admins.db'}")
    await database_manager.create_all()
    message = MagicMock(spec=types.Message)
    message.from_user = types.User(id=9876, is_bot=False, first_name="Guest")
    message.answer = AsyncMock()
    message.text = "/admin add @NewAdmin"

    await admin_command(message, database_manager, set(), set())

    message.answer.assert_awaited_with(
        "❌ You are not authorized to manage admins."
    )
    database_manager.close()


@pytest.mark.asyncio
async def test_set_default_channel_saves_group_for_admin(tmp_path):
    database_manager = DatabaseManager(f"sqlite:///{tmp_path / 'default-channel.db'}")
    await database_manager.create_all()
    message = MagicMock(spec=types.Message)
    message.from_user = types.User(id=12345, is_bot=False, first_name="Admin")
    message.chat = types.Chat(id=-100123, type="supergroup")
    message.answer = AsyncMock()

    await set_default_channel_command(
        message,
        database_manager,
        {"12345"},
        set(),
    )

    with database_manager.get_session() as session:
        destination = session.get(DefaultTournamentChannel, "default")
        assert destination.chat_id == "-100123"
        assert destination.assigned_by == "12345"
    assert "default destination" in message.answer.await_args.args[0]
    database_manager.close()


@pytest.mark.asyncio
async def test_set_default_channel_rejects_private_chat(tmp_path):
    database_manager = DatabaseManager(f"sqlite:///{tmp_path / 'default-channel.db'}")
    await database_manager.create_all()
    message = MagicMock(spec=types.Message)
    message.from_user = types.User(id=12345, is_bot=False, first_name="Admin")
    message.chat = types.Chat(id=12345, type="private")
    message.answer = AsyncMock()

    await set_default_channel_command(
        message,
        database_manager,
        {"12345"},
        set(),
    )

    message.answer.assert_awaited_once()
    assert "in the Telegram group" in message.answer.await_args.args[0]
    database_manager.close()


@pytest.mark.asyncio
async def test_setup_handlers_bootstraps_configured_admins(tmp_path):
    database_manager = DatabaseManager(f"sqlite:///{tmp_path / 'admins.db'}")
    await database_manager.create_all()
    admin_ids = {"12345"}
    admin_usernames = {"poyotcg"}

    await setup_handlers(
        Dispatcher(),
        MagicMock(),
        admin_ids,
        admin_usernames,
        database_manager,
        MagicMock(),
    )

    assert admin_ids == {"12345"}
    assert admin_usernames == {"poyotcg"}
    database_manager.close()


def test_admin_removal_persists_and_preserves_last_admin(tmp_path):
    database_path = tmp_path / "admins.db"
    database_manager = DatabaseManager(f"sqlite:///{database_path}")
    asyncio.run(database_manager.create_all())
    database_manager.initialize_admins({"12345"}, {"poyotcg", "otheradmin"})

    assert database_manager.remove_admin("poyotcg")
    assert database_manager.initialize_admins(
        {"12345"},
        {"poyotcg", "otheradmin"},
    ) == ({"12345"}, {"otheradmin"})

    assert database_manager.remove_admin("otheradmin")
    with pytest.raises(ValueError, match="last admin"):
        database_manager.remove_admin("12345")
    database_manager.close()
