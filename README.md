# TopDeck Tournament Tracker

Telegram bot for TopDeck tournament status and the 2026 Poyo League leaderboard.
The running application uses `aiogram`, the TopDeck Tournaments V2 API, and a
SQLite database.

## Features

- `/status` lists tournaments from the TopDeck account connected by API key.
- `/points` shows every player in the 2026 league standings.
- Monthly events (8 or more players) score the monthly table and award +1
  additional point to each player with no losses in non-bracket rounds. Draws
  do not count as losses; bracket results are ignored.
- Weekly events (7 or fewer players) score the weekly table.
- `/bonus` appends a signed manual point adjustment (positive or negative) to a
  player's league total. Adjustments are persisted with the acting Telegram
  account and timestamp.
- `/admin add` and `/admin remove` manage the persistent bot-admin list.
- `/setdefaultchannel` sets the group for automatically linked TopDeck events.
- Signed TopDeck `tournament.finished` webhooks update tournament results and
  trigger a third-place confirmation in the assigned Telegram destination.
- SQLite persistence for tournaments, player standings, bonus adjustments, and
  notifications.

## Requirements

- Python 3.10 or newer (the Docker image uses Python 3.11).
- A Telegram bot token from [@BotFather](https://t.me/BotFather).
- A TopDeck API key with access to your tournaments.

## Local setup

From the repository root, in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `BOT_TOKEN` and `TOPDECK_API_KEY` in `.env`. Then initialize the configured
database and start the bot:

```powershell
python migrations/init.py
python -m src.main
```

On macOS/Linux, activate the environment with `source .venv/bin/activate` and
copy the template with `cp .env.example .env`.

## Configuration

| Variable | Purpose |
|---|---|
| `BOT_TOKEN` | Telegram bot token (required). |
| `TOPDECK_API_KEY` | TopDeck API key (required). |
| `TOPDECK_API_URL` | API base URL; defaults to `https://topdeck.gg/api`. |
| `TOPDECK_WEBHOOK_SECRET` | TopDeck endpoint's `whsec_...` signing secret; enables the webhook receiver. |
| `TOPDECK_DEFAULT_CHAT_ID` | Default Telegram destination for tournaments without a per-tournament assignment; defaults to `-1004340474920`. |
| `WEBHOOK_HOST` / `WEBHOOK_PORT` | HTTP listener bind address and port (defaults to `0.0.0.0:8080`). |
| `WEBHOOK_BIND_ADDRESS` | Docker host bind address (defaults to `0.0.0.0`, so a reverse proxy on another LAN guest can reach it). |
| `DATABASE_PATH` | SQLite path; defaults to `data/tournaments.db`. |
| `BONUS_ADMIN_IDS` | Comma-separated Telegram user IDs bootstrapped as admins on first startup. |
| `BONUS_ADMIN_USERNAMES` | Comma-separated Telegram usernames bootstrapped as admins on first startup; `poyotcg` is included by default. |
| `DEBUG` | Enables debug logging when set to `true`. |

The Docker Compose service reads `.env` and mounts `./data` at `/app/data`.
Changing environment variables for a running container requires recreating it:

```powershell
docker compose --env-file .env up --detach --build --force-recreate
```

## Bot commands

| Command | Description |
|---|---|
| `/start` | Welcome message and command overview. |
| `/status` | List tournaments returned by the configured TopDeck account. |
| `/points` | Show the complete 2026 Poyo League standings. |
| `/bonus <signed points> <player name or TopDeck ID>` | Admin-only cumulative point adjustment. |
| `/admin <add|remove> <@username or Telegram user ID>` | Add or remove a bot admin; admin-only. |
| `/setdefaultchannel` | Set this group as the default results destination for new events; admin-only. |
| `/assignchannel <TopDeck tournament ID> [chat ID or @channel]` | Assign a results destination; admin-only. |
| `/help` | Show available commands. |

Example adjustments:

```text
/bonus +5 Angel Fuentes
/bonus -3 Angel Fuentes
```

Use `/admin add @username` or `/admin add <Telegram user ID>` to grant admin
access; use `/admin remove` with the same target format to revoke it. These
changes are stored in SQLite and take effect immediately. The configured admins
and `@poyotcg` are used to seed the list when it is first created. The last
remaining admin cannot be removed. The `/bonus` target must match one 2026
league player by exact name (case-insensitive) or TopDeck player ID.

## TopDeck webhook results

1. Ensure the bot is a member of the destination Telegram group and can send
   messages. `TOPDECK_DEFAULT_CHAT_ID` defaults to the configured league group,
   so all tournament results use it automatically, including pending
   completion events. It takes precedence over stored per-tournament
   assignments. To route to another destination, change this setting.
2. In TopDeck's [developer portal](https://topdeck.gg/developers), register an
   HTTPS endpoint at `https://<your-public-host>/webhooks/topdeck` and subscribe
   to both `tournament.checkin_started` and `tournament.finished`. TopDeck
   documents `tournament.checkin_started` (not `tournament.started`) as the
   event that fires when check-in opens. Copy the endpoint's `whsec_...`
   signing secret into `TOPDECK_WEBHOOK_SECRET` in `.env`.
3. Route public HTTPS through your TLS reverse proxy to the bot VM's LAN address
   on port 8080 (`WEBHOOK_BIND_ADDRESS=0.0.0.0` by default), then recreate the
   service. Do not forward the bot VM's webhook port directly from the router;
   public traffic should terminate at the TLS reverse proxy.
   The listener also exposes `/health` for local health checks.

The receiver verifies TopDeck's HMAC signature against the raw request body,
stores event IDs durably to deduplicate retries, and processes events in the
background. If a tournament has no explicit destination, its result handling
assigns the configured default Telegram group and persists that association.
When a tournament finishes, it fetches current rounds from TopDeck,
stores standings in SQLite, and posts a third-place confirmation keyboard. A
bot admin's selection updates third/fourth places and league points, then posts
the final standings to the assigned destination.

TopDeck requires a publicly resolvable HTTPS endpoint. A homelab-only deployment
is not reachable until a public domain and HTTPS ingress (for example a TLS
reverse proxy with a tunnel or router forwarding) are configured. Keep the
webhook signing secret private; do not commit it.

## Tests

Install the project dependencies, then run:

```powershell
python -m pytest
```

## Project layout

- `src/handlers/` — Telegram commands and routing.
- `src/services/` — TopDeck integration, leaderboard, and scoring logic.
- `src/models/` — SQLAlchemy database models and schema initialization.
- `src/topdeck/` — TopDeck Tournaments V2 API client.
- `migrations/` — Database initialization entrypoint.
- `tests/` — Unit and integration tests.
- `docs/` — Quick start, user, development, and architecture guides.

See [the quick start](docs/quickstart.md), [user guide](docs/user-guide.md),
[development guide](docs/development-guide.md), and
[architecture overview](docs/architecture.md).
