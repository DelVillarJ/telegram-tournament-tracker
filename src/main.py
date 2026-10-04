#!/usr/bin/env python3
"""
Telegram Bot for TopDeck Tournament Tracking

Main entry point for the bot application.
"""

import os
import asyncio
from pathlib import Path

from .config import Settings
from .handlers import setup_handlers
from .services.topdeck import TopDeckService
from .models.database import DatabaseManager


async def main():
    """Main async entry point."""
    # Initialize settings from environment
    settings = Settings()
    
    # Setup logging
    setup_logging(settings.debug)
    
    # Initialize database
    db_manager = DatabaseManager(
        url=settings.db_url,
        echo=settings.debug
    )
    await db_manager.create_all()
    
    # Initialize TopDeck service
    topdeck_service = TopDeckService(
        api_key=settings.topdeck_api_key,
        api_url=settings.topdeck_api_url
    )
    
    # Initialize bot
    from aiogram import Bot, Dispatcher
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    
    # Setup handlers
    await setup_handlers(dp, topdeck_service)
    
    print("Bot started!")
    print(f"Bot token: {settings.bot_token[:10]}...")
    print(f"Debug mode: {settings.debug}")
    
    # Run migrations
    await db_manager.run_migrations()
    
    # Start polling
    async with bot:
        await dp.start_polling(bot)


def setup_logging(debug: bool):
    """Setup logging configuration."""
    import logging
    
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG if debug else logging.INFO
    )


if __name__ == "__main__":
    asyncio.run(main())
