# Quick Start Guide

This guide helps you get the Telegram bot running in 5 minutes.

## Prerequisites Checklist

- [ ] Python 3.10+ installed (`python --version`)
- [ ] pip available
- [ ] Telegram account created

## Step 1: Get Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow instructions to create bot
4. Copy the token provided

## Step 2: Setup Environment

```bash
# Create .env file from template
cp .env.template .env

# Edit .env with your values
nano .env  # or use your preferred editor

# Add these lines (replace placeholders):
BOT_TOKEN=your_bot_token_here
TOPDECK_API_KEY=your_api_key_here
TELEGRAM_GROUP_IDS=id1,id2,id3  # Your group IDs
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Initialize Database

```bash
python migrations/init.py
```

Expected output:
```
Initializing database...
Database tables created successfully
✅ Database initialized!
```

## Step 5: Run the Bot

```bash
python src/main.py
```

Expected output:
```
Bot started!
Bot token: abc123...
Debug mode: False
```

## Test the Bot

1. Open Telegram and start your bot (username: `your_botname`)
2. Send `/start` command
3. Try other commands (`/status`, `/points`, `/help`)

## Troubleshooting

### "No module named 'xxx'" error

Run: `pip install -r requirements.txt` again

### Database errors

Check if migrations ran: `python migrations/init.py`

### Bot not responding

1. Check token is correct in `.env`
2. Ensure bot isn't banned (check @BotFather)
3. Try restarting the bot

## Next Steps

- Customize notification settings in `.env`
- Review `/docs/user-guide.md` for full command list
- See `/docs/development-guide.md` for development tips

## Need Help?

- Check existing issues on GitHub
- Review logs in `logs/` directory
- Enable debug mode: set `DEBUG=true` in `.env`
