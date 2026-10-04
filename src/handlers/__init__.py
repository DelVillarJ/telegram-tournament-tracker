"""Telegram bot command and callback handlers."""

from aiogram import F, Router, types
from aiogram.filters.command import Command
from typing import Optional

from .services.topdeck import TopDeckService
from .models.schemas import TournamentStatusResponse


router = Router()


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
        "/notify <group_id> - Set notification group\n"
        "/help - Show this help message",
        parse_mode="Markdown"
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
        
        await message.answer(response_text, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(
            f"❌ Error fetching tournament status:\n{str(e)}",
            parse_mode="Markdown"
        )


@router.message(Command("points"))
async def points_command(message: types.Message, topdeck_service: TopDeckService) -> None:
    """Handle /points command."""
    try:
        # Get latest tournament standings
        standings = await topdeck_service.get_standings()
        
        if not standings:
            await message.answer("📈 No standings available yet.")
            return
        
        response_text = "🏆 Points Standings:\n\n"
        
        for rank, player in enumerate(standings[:10], 1):  # Top 10
            position_emoji = ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else f"{rank}."
            response_text += f"{position_emoji} {player.get('display_name', 'Player')} - "
            response_text += f"{player.get('points', 0)} pts\n"
        
        await message.answer(response_text, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(
            f"❌ Error fetching standings:\n{str(e)}",
            parse_mode="Markdown"
        )


@router.message(Command("help"))
async def help_command(message: types.Message) -> None:
    """Handle /help command."""
    help_text = "🤖 TopDeck Tournament Bot Commands:\n\n"
    help_text += "/start - Initialize bot and get help\n"
    help_text += "/status - Show current tournament status\n"
    help_text += "/points - Display points standings\n"
    help_text += "/notify <group_id> - Set notification group\n"
    help_text += "/help - Show this help message\n\n"
    help_text += "Need support? Contact @bot_support"
    
    await message.answer(help_text, parse_mode="Markdown")


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
                parse_mode="Markdown"
            )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Error: {str(e)}",
            parse_mode="Markdown"
        )
