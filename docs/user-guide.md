# User Guide - Telegram Bot for TopDeck Tournament Tracking

This guide explains how to use the bot commands and features.

## Quick Start

1. **Start the bot**: `/start`
2. **Get help**: Use `/help` command
3. **Check tournaments**: Use `/status` command
4. **View standings**: Use `/points` command

## Available Commands

### `/start`
Initializes the bot and shows available commands.

**Response**: 
```
👋 Welcome to the TopDeck Tournament Bot!

I can help you:
• Track tournament status
• Check points standings
• Get notifications when tournaments finish

Available commands:
/status - Show current tournament status
/points - Display points standings
/notify <group_id> - Set notification group
/help - Show this help message
```

### `/status`
Shows all active tournaments currently tracked from TopDeck.

**Response format**:
```
🏆 Active Tournaments:

1. Summer Grand Prix
   Participants: 50
   Status: active

2. Winter Championship
   Participants: 30
   Status: scheduled
```

### `/points`
Displays the current points standings for active tournaments.

**Response format**:
```
🏆 Points Standings:

🥇 Player1 - 150 pts
🥈 Player2 - 140 pts
🥉 Player3 - 135 pts
4. Player4 - 120 pts
```

### `/help`
Shows this help message with all available commands.

## Settings

The bot automatically syncs with your TopDeck account. No additional setup needed.

To configure which groups receive notifications, set `TELEGRAM_GROUP_IDS` in `.env`.

## Tips

- Use `/status` to check if tournaments are active
- Standings update automatically when new events complete
- Enable debug mode (`DEBUG=true`) for detailed logs during development
