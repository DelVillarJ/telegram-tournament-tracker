"""
Telegram Bot initialization and command handlers.
Sets up the bot with Telegram Bot API and registers all command handlers.
"""

import logging
from typing import List, Optional
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.error import BadRequest


# Import our custom configuration and database modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import config
from src.database import (
    init_database,
    get_active_tournaments,
    get_tournament_by_id,
    mark_tournament_completed,
    archive_tournament,
    update_tournament_status,
    add_player,
    get_standings_for_tournament,
    update_standings,
)


# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO if not config.debug else logging.DEBUG
)
logger = logging.getLogger(__name__)


async def start_command(update: Update) -> None:
    """
    Handle /start command.
    
    Sends welcome message and shows help to new users.
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Initialize database if not done yet
    try:
        init_database()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    welcome_message = (
        f"👋 *Welcome to the Tournament Tracker Bot!*\n\n"
        f"Hi @{update.effective_user.username or str(user_id)}!\n\n"
        f"Bot features:\n"
        "• Track TopDeck tournaments hosted by specific users\n"
        "• Get notifications when tournaments complete\n"
        "• View current standings and points\n"
        "\n"
        f"*Available Commands*:\n"
        "/start - This help message\n"
        "/status - Show active tournaments\n"
        "/standings - Display current standings\n"
        "/tournaments - List all tracked tournaments\n"
        "/help - Show this help message\n"
    )
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')


async def status_command(update: Update) -> None:
    """
    Handle /status command.
    
    Shows current active tournaments.
    """
    tournaments = get_active_tournaments(config.get_target_user_ids())
    
    if not tournaments:
        message = "📊 *No active tournaments*\n\nCurrently no tournaments in progress."
    else:
        message = "🏆 *Active Tournaments*\n\n"
        for i, tourney in enumerate(tournaments, 1):
            status_icon = {
                'ongoing': '🔴',
                'pending': '⏳',
                'cancelled': '❌'
            }.get(tourney['status'], '❓')
            
            message += (
                f"*{i}. {tourney['name']}*\n"
                f"{status_icon} {tourney['category'] or 'General'}\n"
                f"ID: {tourney['topdeck_tournament_id']}\n"
                f"Status: {tourney['status'].capitalize()}\n\n"
            )
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def standings_command(update: Update) -> None:
    """
    Handle /standings command.
    
    Shows points standings for active tournaments.
    """
    tournaments = get_active_tournaments(config.get_target_user_ids())
    
    if not tournaments:
        message = "📊 *No standings available*\n\nCurrently no active tournaments to display standings."
    else:
        message = "🏆 *Tournament Standings*\n\n"
        
        for tourney in tournaments:
            tournament_id = tourney['id']
            
            # Get standings for this tournament
            standings = get_standings_for_tournament(tournament_id)
            
            if not standings:
                continue
            
            message += (
                f"*{tourney['name']}*\n"
                f"_ID: {tourney['topdeck_tournament_id']}_\n\n"
            )
            
            for i, standing in enumerate(standings, 1):
                points = standing.get('points', 0) or standing.get('points', '')
                message += (
                    f"*{i}. {standing['team_name']}*{' 🥇' if i==1 else ''}\n"
                    f"Points: {points}" + (f"\nGames: {standing.get('games_played') or 0}" if standing.get('games_played') else "")
                )
            message += "\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def tournaments_command(update: Update) -> None:
    """
    Handle /tournaments command.
    
    Shows all tracked tournaments including archived ones.
    """
    # Get active and archived tournaments
    all_tournaments = get_active_tournaments(config.get_target_user_ids())
    
    # Also include completed/archived from history
    cursor_name = "sqlite3"
    import sqlite3
    
    db_path = Path(__file__).parent.parent / 'data' / 'tournaments.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT topdeck_tournament_id, name, category, status, start_date, end_date
        FROM tournaments
        WHERE id NOT IN (
            SELECT tournament_id FROM history_archive
        )
        ORDER BY start_date DESC
    ''')
    
    additional = cursor.fetchall()
    all_tournaments.extend(additional)
    
    conn.close()
    
    if not all_tournaments:
        message = "📊 *No tournaments tracked*\n\nCurrently no tournaments are being tracked."
    else:
        message = "🏆 *All Tracked Tournaments*\n\n"
        
        for i, tourney in enumerate(all_tournaments, 1):
            if isinstance(tourney, dict):
                status_icon = {
                    'ongoing': '🔴',
                    'pending': '⏳',
                    'completed': '✅',
                    'cancelled': '❌'
                }.get(tourney.get('status', ''), '❓')
                
                message += (
                    f"*{i}. {tourney['name']}*\n"
                    f"{status_icon} {tourney.get('category', '')}\n\n"
                )
            else:
                # Legacy tuple format
                status_icons = {'ongoing': '🔴', 'pending': '⏳', 'completed': '✅'}
                status_icon = status_icons.get(tourney[2], '❓')
                
                message += (
                    f"*{i}. {tourney[1]}*\n"
                    f"{status_icon} {tourney[3]}\n\n"
                )
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def help_command(update: Update) -> None:
    """
    Handle /help command.
    
    Shows all available commands and usage instructions.
    """
    help_message = (
        f"🤖 *Tournament Tracker Bot*\n\n"
        f"*Commands*:\n\n"
        f"/start - Show this help message\n"
        f"/status - Display active tournaments\n"
        f"/standings - Show current standings\n"
        f"/tournaments - List all tracked tournaments\n"
        f"/help - Show command help\n\n"
        
        f"*Usage Examples*:\n\n"
        f"- `/status` - See what tournaments are currently active\n"
        f"- `/standings` - View points standings\n"
        f"- `/tournaments` - Manage tournament tracking\n\n"
        
        f"💡 *Notifications*:\n\n"
        f"The bot will automatically notify you when:\n"
        f"• A new tournament starts\n"
        f"• A tournament is completed\n"
        f"• A tournament is cancelled\n\n"
    )
    
    await update.message.reply_text(help_message, parse_mode='Markdown')


async def invalid_command(update: Update) -> None:
    """
    Handle unknown commands.
    
    Shows usage reminder to users with invalid commands.
    """
    help_snippet = (
        f"❓ *Unknown Command*\n\n"
        f"I don't understand that command. Try:\n"
        "/start, /status, /standings, /tournaments, /help"
    )
    
    await update.message.reply_text(help_snippet, parse_mode='Markdown')


async def add_tournament_command(update: Update) -> None:
    """
    Handle /add-tournament <tournament_id> command.
    
    Manually add a tournament to tracking.
    """
    match = update.effective_text.split()
    
    if len(match) < 2:
        await update.message.reply_text(
            "❓ *Usage:* `/add-tournament <tournament_id>`\n\n"
            "Example: `/add-tournament 12345`",
            parse_mode='Markdown'
        )
        return
    
    tournament_id = match[1]
    
    try:
        # For now, just acknowledge the request
        # In production, this would need to integrate with TopDeck API
        await update.message.reply_text(
            f"🔍 *Searching for tournament*...\n\n"
            f"Tournament ID: `{tournament_id}`\n"
            f"Please ensure you have proper credentials configured.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to add tournament {tournament_id}: {e}")
        await update.message.reply_text(
            f"❌ Error adding tournament: {str(e)}",
            parse_mode='Markdown'
        )


async def remove_tournament_command(update: Update) -> None:
    """
    Handle /remove-tournament <tournament_id> command.
    
    Remove a tournament from tracking.
    """
    match = update.effective_text.split()
    
    if len(match) < 2:
        await update.message.reply_text(
            "❓ *Usage:* `/remove-tournament <tournament_id>`\n\n"
            "Example: `/remove-tournament 12345`",
            parse_mode='Markdown'
        )
        return
    
    tournament_id = match[1]
    
    try:
        # Archive the tournament (soft delete)
        db_tourney = get_tournament_by_id(int(tournament_id))
        
        if not db_tourney:
            await update.message.reply_text(
                f"❌ Tournament `{tournament_id}` not found in tracking list.",
                parse_mode='Markdown'
            )
            return
        
        # Archive it
        archive_tournament(db_tourney['id'])
        
        await update.message.reply_text(
            f"✅ Tournament removed from active tracking.\n\n"
            f"Tournament: `{db_tourney['topdeck_tournament_id']}`\n"
            f"Name: {db_tourney['name']}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to remove tournament {tournament_id}: {e}")
        await update.message.reply_text(
            f"❌ Error removing tournament: {str(e)}",
            parse_mode='Markdown'
        )


async def handle_regular_message(update: Update) -> None:
    """
    Handle regular (non-command) messages.
    
    Can be extended for chat members, welcome messages, etc.
    """
    chat_id = update.effective_chat.id
    
    # Add simple welcome for new members
    if 'new_chat_member' in update.effective_message.to_dict():
        member = update.effective_message.from_user
        await update.message.reply_text(
            f"👋 Welcome @{member.username or str(member.id)}!",
            parse_mode='Markdown'
        )


def create_application() -> Application:
    """
    Create and configure the Telegram application.
    
    Returns:
        Application object with registered handlers.
    """
    # Apply configuration from .env file (using SQLite database)
    app = Application.builder().token(config.bot_token).build()
    
    # Register command handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('status', status_command))
    app.add_handler(CommandHandler('standings', standings_command))
    app.add_handler(CommandHandler('tournaments', tournaments_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('invalid', invalid_command))
    app.add_handler(CommandHandler('add-tournament', add_tournament_command))
    app.add_handler(CommandHandler('remove-tournament', remove_tournament_command))
    
    # Add filter for regular messages (non-commands)
    app.add_handler(
        MessageHandler(filters.COMMAND & filters.Regex(r'^(?!start|status|standings|tournaments|help|add-tournament|remove-tournament)$'), 
                       invalid_command)
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_regular_message))
    
    return app


def initialize_bot() -> Application:
    """
    Initialize and start the bot.
    
    Returns:
        Application object ready to run.
    """
    try:
        app = create_application()
        print(f"✅ Bot started! Token length: {len(config.bot_token)}")
        
        # Show active tournaments if any
        tournaments = get_active_tournaments(config.get_target_user_ids())
        if tournaments:
            print(f"📊 Monitoring {len(tournaments)} active tournament(s)")
        
        return app
        
    except BadRequest as e:
        logger.error(f"Invalid bot token: {e}")
        raise ValueError("Invalid bot token. Please check your .env file.")
    except Exception as e:
        logger.error(f"Bot initialization failed: {e}")
        raise


if __name__ == '__main__':
    try:
        # Initialize and run the bot
        app = initialize_bot()
        
        # Start polling for updates (in production, use a proper process manager)
        print("\n🤖 Bot is now running...")
        print("Press Ctrl+C to stop\n")
        
        # This will block until stopped
        try:
            while True:
                # Keep the bot running - in production use supervisor/systemd
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Stopping bot...")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
