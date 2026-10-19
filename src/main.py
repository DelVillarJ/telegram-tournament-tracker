#!/usr/bin/env python3
"""
Telegram Bot for TopDeck Tournament Tracking

Main entry point for the bot application.
"""

import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher

from .config import config as settings
from .handlers import setup_handlers
from .services.topdeck import TopDeckService
from .services.topdeck_webhook import TopDeckWebhookService
from .models.database_manager import DatabaseManager


async def main():
    """Main async entry point."""
    setup_logging(settings.debug)
    settings.ensure_db_directory()
    db_manager = DatabaseManager(
        url=settings.get_database_url(),
        echo=settings.debug,
    )
    try:
        await db_manager.run_migrations()
        topdeck_service = TopDeckService(
            api_key=settings.topdeck_api_key,
            api_url=settings.topdeck_api_url,
            database_manager=db_manager,
        )

        bot = Bot(token=settings.bot_token)
        dp = Dispatcher()
        webhook_service = TopDeckWebhookService(
            database_manager=db_manager,
            bot=bot,
            api_client=topdeck_service.api_client,
            signing_secret=settings.topdeck_webhook_secret,
            default_chat_id=settings.topdeck_default_chat_id,
        )
        await setup_handlers(
            dp,
            topdeck_service,
            settings.bonus_admin_ids,
            settings.bonus_admin_usernames,
            db_manager,
            webhook_service,
        )

        async with bot:
            runner = None
            if settings.topdeck_webhook_secret:
                runner = web.AppRunner(webhook_service.create_app())
                await runner.setup()
                site = web.TCPSite(
                    runner,
                    settings.webhook_host,
                    settings.webhook_port,
                )
                await site.start()
                logging.getLogger(__name__).info(
                    "TopDeck webhook listener started on %s:%s",
                    settings.webhook_host,
                    settings.webhook_port,
                )
            else:
                logging.getLogger(__name__).warning(
                    "TopDeck webhook receiver is disabled; "
                    "set TOPDECK_WEBHOOK_SECRET to enable it."
                )
            try:
                await _run_polling_with_worker(dp, bot, webhook_service)
            finally:
                if runner is not None:
                    await runner.cleanup()
    finally:
        db_manager.close()


async def _run_polling_with_worker(
    dispatcher: Dispatcher,
    bot: Bot,
    webhook_service: TopDeckWebhookService,
) -> None:
    polling = asyncio.create_task(dispatcher.start_polling(bot))
    worker = asyncio.create_task(webhook_service.run_worker())
    try:
        done, _ = await asyncio.wait(
            {polling, worker},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if worker in done:
            worker.result()
            raise RuntimeError("TopDeck webhook worker stopped unexpectedly.")
        polling.result()
    finally:
        for task in (polling, worker):
            if not task.done():
                task.cancel()
        await asyncio.gather(polling, worker, return_exceptions=True)


def setup_logging(debug: bool):
    """Setup logging configuration."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG if debug else logging.INFO
    )


if __name__ == "__main__":
    asyncio.run(main())
