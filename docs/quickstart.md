# Quick start

## Requirements

- Python 3.11 or newer.
- A Telegram bot token from [@BotFather](https://t.me/BotFather).
- A TopDeck API key.

## Install and configure

Run these commands from the repository root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set the required values:

```dotenv
BOT_TOKEN=your_telegram_bot_token
TOPDECK_API_KEY=your_topdeck_api_key
TOPDECK_API_URL=https://topdeck.gg/api
```

## Initialize and run

```powershell
python migrations/init.py
python -m src.main
```

Open the bot in Telegram, send `/start`, then try `/status` or `/points`.
`/points` reads the 2026 standings from the configured SQLite database. See
the [user guide](user-guide.md) for scoring and the admin bonus command.

## Docker

After setting the required values in `.env`:

```powershell
docker compose --env-file .env up --detach --build
docker compose logs --follow telegram-bot
```

To apply changed environment values to an existing container:

```powershell
docker compose --env-file .env up --detach --build --force-recreate
```

The database is stored in `data/tournaments.db` on the host and mounted into the
container. The bot uses Telegram long polling; it does not expose an HTTP health
endpoint.

On macOS/Linux, activate with `source .venv/bin/activate` and copy the template
with `cp .env.example .env`.
