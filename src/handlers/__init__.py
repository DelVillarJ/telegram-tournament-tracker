"""Telegram bot command and callback handlers."""

import logging
import re

from aiogram import F, Router, types, Dispatcher
from aiogram.filters.command import Command
from sqlalchemy.exc import SQLAlchemyError

from src.services.topdeck import TopDeckService
from src.models.database_manager import DatabaseManager
from src.models.database import DefaultTournamentChannel, TournamentChannel
from src.services.topdeck_webhook import TopDeckWebhookService

router = Router()
logger = logging.getLogger(__name__)

async def setup_handlers(
    dp: Dispatcher,
    topdeck_service: TopDeckService,
    bonus_admin_ids: set[str],
    bonus_admin_usernames: set[str],
    database_manager: DatabaseManager,
    topdeck_webhook_service: TopDeckWebhookService,
) -> None:
    """Register all bot handlers."""
    configured_admin_ids = set(bonus_admin_ids)
    configured_admin_usernames = set(bonus_admin_usernames)
    admin_ids, admin_usernames = database_manager.initialize_admins(
        configured_admin_ids,
        configured_admin_usernames,
    )
    bonus_admin_ids.clear()
    bonus_admin_usernames.clear()
    bonus_admin_ids.update(admin_ids)
    bonus_admin_usernames.update(admin_usernames)
    dp.include_router(router)

    async def inject_topdeck_service(handler, event, data):
        data['topdeck_service'] = topdeck_service
        data['bonus_admin_ids'] = bonus_admin_ids
        data['bonus_admin_usernames'] = bonus_admin_usernames
        data['database_manager'] = database_manager
        data['topdeck_webhook_service'] = topdeck_webhook_service
        return await handler(event, data)

    dp.message.middleware(inject_topdeck_service)
    dp.callback_query.middleware(inject_topdeck_service)

@router.message(Command("start"))
async def start_command(message: types.Message) -> None:
    """Handle /start command."""
    await message.answer(
        "👋 Welcome to the TopDeck Tournament Bot!\n\n"
        "I can help you:\n"
        "• Track tournament status\n"
        "• Check points standings\n"
        "• Get notifications when tournaments finish\n\n"
        "Available commands:\n"
        "/status - Show current tournament status\n"
        "/points - Display points standings\n"
        "/setdefaultchannel - Set this group as the default results destination\n"
        "/admin <add|remove> <@username or Telegram user ID> - Manage admins\n"
        "/notify &lt;group_id&gt; - Set notification group\n"
        "/help - Show this help message",
        parse_mode="HTML"
    )


@router.message(Command("status"))
async def status_command(message: types.Message, topdeck_service: TopDeckService) -> None:
    """Handle /status command."""
    try:
        tournaments = await topdeck_service.get_active_tournaments()
        
        if not tournaments:
            await message.answer("📊 No active tournaments found.")
            return
        
        response_text = "🏆 Active Tournaments:\n\n"
        for i, tournament in enumerate(tournaments[:5], 1):  # Limit to first 5
            response_text += f"{i}. {tournament['name']}\n"
            response_text += f"   Participants: {tournament.get('participant_count', 'N/A')}\n"
            response_text += f"   Status: {tournament.get('status', 'Unknown')}\n\n"
        
        if len(tournaments) > 5:
            response_text += f"... and {len(tournaments) - 5} more tournaments"
        
        await message.answer(response_text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(
            f"❌ Error fetching tournament status:\n{str(e)}",
            parse_mode="HTML"
        )


@router.message(Command("points"))
async def points_command(message: types.Message, topdeck_service: TopDeckService) -> None:
    """Handle /points command."""
    try:
        standings = await topdeck_service.get_league_standings(year=2026)
        
        if not standings:
            await message.answer("📈 No standings available yet.")
            return
        
        response_text = "🏆 2026 Poyo League Standings:\n\n"
        
        for rank, player in enumerate(standings, 1):
            position_emoji = ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else f"{rank}."
            response_text += f"{position_emoji} {player.get('player_name', 'Player')} - "
            response_text += f"{player.get('points', 0)} pts"
            bonus_points = player.get("bonus_points", 0)
            if bonus_points:
                response_text += f" (incl. {bonus_points:+d} bonus)"
            response_text += " "
            response_text += f"({player.get('events_played', 0)} events)\n"
        
        await message.answer(response_text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(
            f"❌ Error fetching standings:\n{str(e)}",
            parse_mode="HTML"
        )


@router.message(Command("bonus"))
async def bonus_command(
    message: types.Message,
    topdeck_service: TopDeckService,
    bonus_admin_ids: set[str],
    bonus_admin_usernames: set[str],
) -> None:
    """Apply a manual signed point adjustment to a 2026 league player."""
    user = message.from_user
    if user is None:
        await message.answer("❌ You are not authorized to adjust league points.")
        return
    is_admin = str(user.id) in bonus_admin_ids or (
        user.username is not None
        and user.username.casefold() in bonus_admin_usernames
    )
    if not is_admin:
        await message.answer("❌ You are not authorized to adjust league points.")
        return

    parts = (message.text or "").split(maxsplit=2)
    if len(parts) != 3:
        await message.answer(
            "Usage: /bonus <signed points> <exact player name or TopDeck player ID>\n"
            "Example: /bonus -3 Angel Fuentes"
        )
        return

    try:
        points = int(parts[1])
    except ValueError:
        await message.answer("❌ Points must be a non-zero whole number, such as +5 or -3.")
        return

    if points == 0:
        await message.answer("❌ Points must be a non-zero whole number, such as +5 or -3.")
        return

    try:
        adjustment = await topdeck_service.add_bonus_points(
            parts[2].strip(),
            points,
            added_by=str(user.id),
        )
        await message.answer(
            f"✅ Adjusted {adjustment['player_name']} by {points:+d} points. "
            f"Bonus total: {adjustment['bonus_points']:+d}; "
            f"league total: {adjustment['total_points']}."
        )
    except ValueError as error:
        await message.answer(f"❌ {error}")
    except Exception as error:
        await message.answer(
            f"❌ Error adjusting league points:\n{error}",
            parse_mode="HTML",
        )


def _normalize_admin_identifier(value: str) -> tuple[str, str] | None:
    """Return a canonical ID or username, and its identifier category."""
    candidate = value.strip()
    if re.fullmatch(r"[0-9]+", candidate):
        numeric_id = candidate.lstrip("0")
        if 1 <= len(numeric_id) <= 20:
            return numeric_id, "id"
        return None

    username = candidate[1:] if candidate.startswith("@") else candidate
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{4,31}", username):
        return username.casefold(), "username"
    return None


@router.message(Command("admin"))
async def admin_command(
    message: types.Message,
    database_manager: DatabaseManager,
    bonus_admin_ids: set[str],
    bonus_admin_usernames: set[str],
) -> None:
    """Add or remove a Telegram account from the persistent admin list."""
    user = message.from_user
    if user is None or (
        str(user.id) not in bonus_admin_ids
        and (
            user.username is None
            or user.username.casefold() not in bonus_admin_usernames
        )
    ):
        await message.answer("❌ You are not authorized to manage admins.")
        return

    parts = (message.text or "").split()
    if len(parts) != 3 or parts[1].casefold() not in {"add", "remove"}:
        await message.answer(
            "Usage: /admin <add|remove> <@username or Telegram user ID>"
        )
        return

    normalized = _normalize_admin_identifier(parts[2])
    if normalized is None:
        await message.answer(
            "❌ Enter a valid Telegram username (with or without @) "
            "or a positive numeric user ID."
        )
        return

    identifier, identifier_type = normalized
    try:
        if parts[1].casefold() == "add":
            added = database_manager.add_admin(identifier, str(user.id))
            if not added:
                await message.answer("That account is already an admin.")
                return
            if identifier_type == "id":
                bonus_admin_ids.add(identifier)
            else:
                bonus_admin_usernames.add(identifier)
            await message.answer(f"✅ Added {parts[2]} as an admin.")
            return

        removed = database_manager.remove_admin(identifier)
        if not removed:
            await message.answer("That account is not an admin.")
            return
        if identifier_type == "id":
            bonus_admin_ids.discard(identifier)
        else:
            bonus_admin_usernames.discard(identifier)
        await message.answer(f"✅ Removed {parts[2]} as an admin.")
    except ValueError as error:
        await message.answer(f"❌ {error}")
    except SQLAlchemyError:
        logger.exception("Failed to update admins")
        await message.answer("❌ Could not update admins. Please try again later.")


@router.message(Command("assignchannel"))
async def assign_channel_command(
    message: types.Message,
    database_manager: DatabaseManager,
    bonus_admin_ids: set[str],
    bonus_admin_usernames: set[str],
) -> None:
    """Assign a Telegram group/channel to a TopDeck tournament."""
    user = message.from_user
    if user is None or (
        str(user.id) not in bonus_admin_ids
        and (
            user.username is None
            or user.username.casefold() not in bonus_admin_usernames
        )
    ):
        await message.answer("❌ You are not authorized to assign destinations.")
        return

    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 2:
        await message.answer(
            "Usage: /assignchannel <TopDeck tournament ID> "
            "[Telegram chat ID or @channel]"
        )
        return

    tournament_id = parts[1].strip()
    chat_id = parts[2].strip() if len(parts) == 3 else str(message.chat.id)
    if not tournament_id or not (
        chat_id.startswith("@")
        or re.fullmatch(r"-?[0-9]{1,20}", chat_id)
    ):
        await message.answer(
            "❌ Use a valid tournament ID and a Telegram chat ID or @channel."
        )
        return

    try:
        with database_manager.get_session() as session:
            channel = session.get(TournamentChannel, tournament_id)
            if channel is None:
                session.add(
                    TournamentChannel(
                        tournament_id=tournament_id,
                        chat_id=chat_id,
                        assigned_by=str(user.id),
                    )
                )
            else:
                session.merge(
                    TournamentChannel(
                        tournament_id=tournament_id,
                        chat_id=chat_id,
                        assigned_by=str(user.id),
                    )
                )
            session.commit()
        await message.answer(
            f"✅ Tournament {tournament_id} will post results to {chat_id}."
        )
    except SQLAlchemyError:
        logger.exception("Failed to assign Telegram destination")
        await message.answer("❌ Could not assign that destination.")


@router.message(Command("setdefaultchannel"))
async def set_default_channel_command(
    message: types.Message,
    database_manager: DatabaseManager,
    bonus_admin_ids: set[str],
    bonus_admin_usernames: set[str],
) -> None:
    """Set the Telegram group for automatically discovered tournaments."""
    user = message.from_user
    if user is None or (
        str(user.id) not in bonus_admin_ids
        and (
            user.username is None
            or user.username.casefold() not in bonus_admin_usernames
        )
    ):
        await message.answer("❌ You are not authorized to set the default destination.")
        return

    if message.chat.type not in {"group", "supergroup"}:
        await message.answer(
            "❌ Run /setdefaultchannel in the Telegram group that should receive "
            "tournament results."
        )
        return

    try:
        with database_manager.get_session() as session:
            destination = session.get(DefaultTournamentChannel, "default")
            if destination is None:
                destination = DefaultTournamentChannel(
                    id="default",
                    chat_id=str(message.chat.id),
                    assigned_by=str(user.id),
                )
                session.add(destination)
            else:
                destination.chat_id = str(message.chat.id)
                destination.assigned_by = str(user.id)
            session.commit()
        await message.answer(
            "✅ This group is now the default destination for new TopDeck "
            "tournaments. Existing tournament assignments are unchanged."
        )
    except SQLAlchemyError:
        logger.exception("Failed to set default Telegram destination")
        await message.answer("❌ Could not set the default destination.")


@router.callback_query(F.data.startswith("third:"))
async def third_place_callback(
    callback: types.CallbackQuery,
    topdeck_webhook_service: TopDeckWebhookService,
    bonus_admin_ids: set[str],
    bonus_admin_usernames: set[str],
) -> None:
    """Let a bot admin confirm the third-place finisher."""
    user = callback.from_user
    if (
        str(user.id) not in bonus_admin_ids
        and (
            user.username is None
            or user.username.casefold() not in bonus_admin_usernames
        )
    ):
        await callback.answer("Only bot admins can confirm third place.", show_alert=True)
        return

    parts = (callback.data or "").split(":")
    if len(parts) != 3 or not parts[2].isdigit():
        await callback.answer("Invalid third-place selection.", show_alert=True)
        return

    try:
        response = await topdeck_webhook_service.confirm_third_place(
            parts[1],
            int(parts[2]),
            str(user.id),
        )
    except Exception:
        logger.exception("Failed to confirm tournament third place")
        await callback.answer("Could not save the result; please try again.", show_alert=True)
        return
    await callback.answer(response)


@router.message(Command("help"))
async def help_command(message: types.Message) -> None:
    """Handle /help command."""
    help_text = "🤖 TopDeck Tournament Bot Commands:\n\n"
    help_text += "/start - Initialize bot and get help\n"
    help_text += "/status - Show current tournament status\n"
    help_text += "/points - Display points standings\n"
    help_text += "/bonus <signed points> <player name or TopDeck ID> - Admin point adjustment\n"
    help_text += "/admin <add|remove> <@username or Telegram user ID> - Manage admins\n"
    help_text += "/setdefaultchannel - Set this group as the default results destination\n"
    help_text += "/assignchannel <TopDeck tournament ID> [chat ID or @channel] - Set result destination\n"
    help_text += "/notify &lt;group_id&gt; - Set notification group\n"
    help_text += "/help - Show this help message\n\n"
    help_text += "Need support? Contact @bot_support"
    
    await message.answer(help_text, parse_mode="HTML")


@router.callback_query(F.data.startswith("tourney_"))
async def tournament_callback(callback: types.CallbackQuery) -> None:
    """Handle tournament-specific callbacks."""
    # Extract tournament ID from callback data
    tourney_id = callback.data.split("_")[1]
    
    await callback.answer()
    
    # Get tournament details and send to user
    try:
        topdeck_service = callback.message.context.topdeck_service
        response = await topdeck_service.get_tournament_details(tourney_id)
        
        if response:
            await callback.message.edit_text(
                f"📊 {response['name']}\n\n"
                f"Status: {response.get('status', 'Unknown')}\n"
                f"Participants: {response.get('participant_count', 'N/A')}",
                parse_mode="HTML"
            )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Error: {str(e)}",
            parse_mode="HTML"
        )
