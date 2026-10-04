"""Notification service for Telegram group management."""

import os
import logging
from typing import Optional, List
from datetime import datetime

from aiogram import Bot, types
from aiogram.client.default import DefaultBotProperties

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications to Telegram groups."""
    
    def __init__(
        self, 
        bot_token: str, 
        default_group_ids: Optional[List[str]] = None,
        bot_properties: Optional[DefaultBotProperties] = None
    ):
        self.bot_token = bot_token
        self.default_group_ids = default_group_ids or []
        
        # Initialize bot
        self.bot = Bot(token=bot_token, defaults=bot_properties)
    
    async def send_to_groups(
        self, 
        message: str,
        group_ids: Optional[List[str]] = None,
        priority: str = "normal"
    ) -> bool:
        """Send notification to specified groups or default groups.
        
        Args:
            message: Message text to send
            group_ids: List of Telegram group/channel IDs (optional)
            priority: Notification priority (low, normal, high)
            
        Returns:
            True if sent successfully, False otherwise
        """
        ids_to_use = group_ids or self.default_group_ids
        
        if not ids_to_use:
            logger.warning("No group IDs provided for notification")
            return False
        
        success_count = 0
        
        # Send to each group/channel
        for group_id in ids_to_use:
            try:
                await self.bot.send_message(
                    chat_id=group_id,
                    text=message,
                    parse_mode="Markdown" if not self._contains_forbidden_chars(message) else "HTML",
                    disable_notification=True,  # Don't ping the group
                    reply_markup=self._create_reaction_keyboard(priority)
                )
                success_count += 1
                logger.info(f"Message sent to group: {group_id}")
                
            except Exception as e:
                logger.error(f"Failed to send to {group_id}: {e}")
                continue
        
        return success_count > 0
    
    async def notify_tournament_complete(
        self, 
        tournament_id: str,
        name: str,
        participant_count: int,
        end_time: Optional[datetime] = None
    ) -> bool:
        """Send completion notification for a tournament.
        
        Args:
            tournament_id: TopDeck tournament ID
            name: Tournament name
            participant_count: Number of participants
            end_time: When the tournament ended
            
        Returns:
            True if notifications sent successfully
        """
        message = (
            f"🏆 Tournament Complete!\n\n"
            f"<b>{name}</b>\n\n"
            f"Participants: {participant_count}\n"
        )
        
        if end_time:
            message += f"Ended at: {end_time.strftime('%Y-%m-%d %H:%M')}"
        
        message += "\n\nCheck the tournament details for standings!"
        
        return await self.send_to_groups(message, priority="high")
    
    async def notify_standings_updated(
        self, 
        tournament_id: str,
        top_5_players: List[dict]
    ) -> bool:
        """Send standings update notification.
        
        Args:
            tournament_id: TopDeck tournament ID
            top_5_players: List of top 5 player dictionaries
            
        Returns:
            True if notifications sent successfully
        """
        message = "📊 Standings Update:\n\n"
        
        for i, player in enumerate(top_5_players[:5], 1):
            emoji = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i}."
            message += f"{emoji} {player.get('display_name', 'Player')} - {player.get('points', 0)} pts\n"
        
        return await self.send_to_groups(message)
    
    async def notify_new_tournament(
        self, 
        tournament_id: str,
        name: str,
        start_time: datetime,
        participant_count: int
    ) -> bool:
        """Send new tournament notification.
        
        Args:
            tournament_id: TopDeck tournament ID
            name: Tournament name
            start_time: Tournament start time
            participant_count: Current participant count
            
        Returns:
            True if notifications sent successfully
        """
        message = (
            f"🆕 New Tournament Available!\n\n"
            f"<b>{name}</b>\n\n"
            f"Starts: {start_time.strftime('%Y-%m-%d %H:%M')}\n"
            f"Current Participants: {participant_count}\n\n"
            f"Check `/status` for details!"
        )
        
        return await self.send_to_groups(message, priority="normal")
    
    async def notify_group_settings(
        self, 
        group_id: str,
        settings: dict
    ) -> bool:
        """Send notification that group settings were updated.
        
        Args:
            group_id: Telegram group ID
            settings: Dictionary of new settings
            
        Returns:
            True if sent successfully
        """
        message = (
            f"⚙️ Settings Updated!\n\n"
            f"You're now receiving notifications from this bot.\n"
            f"Check the available commands with `/help`."
        )
        
        return await self.send_to_groups(message)
    
    def _contains_forbidden_chars(self, text: str) -> bool:
        """Check if text contains characters that require HTML parse mode."""
        forbidden = ['<', '>', '&']
        return any(char in text for char in forbidden)
    
    def _create_reaction_keyboard(self, priority: str) -> Optional[types.InlineKeyboardMarkup]:
        """Create reaction keyboard based on priority.
        
        Args:
            priority: Notification priority (low, normal, high)
            
        Returns:
            InlineKeyboardMarkup or None
        """
        if priority == "high":
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            keyboard.add(types.InlineKeyboardButton(
                text="🚨 High Priority",
                callback_data="reaction:high"
            ))
            return keyboard
    
    async def stop_notifications(self, group_id: str) -> bool:
        """Delete message to indicate notifications stopped.
        
        Args:
            group_id: Telegram group ID
            
        Returns:
            True if successful
        """
        try:
            await self.bot.delete_message(
                chat_id=group_id,
                message_id=self._get_last_message_id(group_id)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to stop notifications for {group_id}: {e}")
            return False
    
    async def get_last_message_id(self, group_id: str) -> Optional[int]:
        """Get the last message ID from a group (for cleanup).
        
        Args:
            group_id: Telegram group ID
            
        Returns:
            Last message ID or None
        """
        try:
            messages = await self.bot.get_chat_history(
                chat_id=group_id,
                limit=1
            )
            return messages.messages[0].message_id if messages.messages else None
        except Exception:
            return None
