# Telegram Bot - TopDeck Tournament Tracker

A Python-based Telegram bot that integrates with the [TopDeck API](https://topdeck.gg/) to track tournaments, notify when they finish, and update points standings for your group.

## Features

- 🤖 **Telegram Integration**: Full bot functionality using python-telegram-bot
- 🏆 **Tournament Tracking**: Monitor all tournaments hosted by specific users on TopDeck
- 🔔 **Notifications**: Automatic notifications when tournaments complete
- 📊 **Points System**: Track and update standings (logic will be implemented later)
- 💾 **SQLite Persistence**: SQLite database for local data storage
- ⚙️ **Flexible Configuration**: Environment-based configuration with secure secret handling
- 🐳 **Docker Ready**: Optional containerization support

## Project Structure

```
telegrambot/
├── README.md                    # This file
├── DEVELOPMENT_GUIDE.md         # Detailed setup and development guide
├── CODE_FLOW_DIAGRAM.mmd        # Mermaid diagram of bot architecture
├── requirements.txt             # Python dependencies
├── docker-compose.yml           # Docker deployment configuration
├── .env.example                 # Environment variable template
├── .gitignore                   # Git ignore rules
│
├── src/
│   ├── __init__.py
│   ├── config.py                # Configuration loader
│   ├── database.py              # Database schema and queries (SQLite)
│   ├── bot.py                   # Main bot initialization and commands
│   ├── topdeck_api.py           # TopDeck API integration
│   ├── tournament_tracker.py    # Tournament detection and tracking
│   ├── points.py                # Point system logic (placeholder - TODO)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py           # Logging configuration
│       └── validators.py        # Input validation helpers
│
├── tests/
│   ├── __init__.py
│   ├── test_database.py         # Database unit tests
│   ├── test_topdeck_api.py      # API client tests
│   └── test_integration.py      # Integration tests
│
└── data/                        # SQLite database storage
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- pip for package management
- Telegram Bot Token (from @BotFather)
- TopDeck API credentials

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd telegrambot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

5. **Run the bot**
   ```bash
   python src/bot.py
   ```

## Configuration

Edit the `.env` file with your credentials:

```bash
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_from_btfather

# TopDeck API Configuration (using SQLite as specified)
TOPDECK_API_URL=https://api.topdeck.gg/v2
TOPDECK_CLIENT_ID=your_client_id_here
TOPDECK_CLIENT_SECRET=your_client_secret_here

# Tournament Tracking Configuration
TARGET_USER_ID=user_id_1,user_id_2  # Comma-separated list of users to track
TOPDECK_POLL_INTERVAL=60             # Seconds between API polling

# Bot Behavior
NOTIFY_ON_COMPLETE=true
AUTO_UPDATE_STANDINGS=true
DEBUG=false                          # Enable debug logging for development

# Database Configuration (SQLite only)
DATABASE_PATH=data/tournaments.db
DB_USE_SQLITE=true
```

## Running the Bot

### Local Development

```bash
python src/bot.py
```

The bot will:
- Listen for Telegram commands and messages
- Poll TopDeck API for new tournament data
- Detect completed tournaments
- Notify your group and update standings

### Using Process Manager (Production)

For production deployment, use a process manager like supervisor or systemd:

1. Create `supervisor.conf`:
   ```ini
   [program:telegram-bot]
   command=python src/bot.py
   directory=/path/to/telegrambot
   user=your-username
   autostart=true
   autorestart=true
   stdout_logfile=/var/log/bot.log
   stderr_logfile=/var/log/bot_error.log
   ```

2. Start supervisor:
   ```bash
   supervisorctl start all
   ```

### Docker Deployment

1. Build and run with docker-compose:
   ```bash
   docker-compose up -d
   ```

## Available Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize the bot and show help |
| `/status` | Show current tournament status |
| `/standings` | Display points standings |
| `/tournaments` | List all tracked tournaments |
| `/add-tournament <id>` | Manually add a tournament |
| `/remove-tournament <id>` | Remove from tracking |
| `/help` | Show command list |

## Code Flow Explanation

1. **Initialization**: Bot loads configuration from `.env`, connects to Telegram and TopDeck API, creates SQLite tables
2. **Command Handlers**: Telegram commands trigger appropriate handlers registered in `bot.py`
3. **Background Polling**: Periodic checks of TopDeck API for tournament updates (configurable interval)
4. **Completion Detection**: Tournament status changes (`completed`) trigger notifications and standings updates
5. **Points Update**: (TODO) Logic calculates points and updates database

See [CODE_FLOW_DIAGRAM.mmd](/c:/Users/jdelv/Documents/python/telegrambot/CODE_FLOW_DIAGRAM.mmd) for detailed architecture.

## Point System (TODO)

The point system logic will be implemented in `src/points.py`. Currently contains placeholder functions:

```python
def calculate_tournament_points(tournament, team):
    """Calculate points earned by a team in a tournament."""
    # TODO: Implement point logic here
    return 0

def update_standings_logic(tournament_id, standings_data):
    """Update standings based on tournament results."""
    # TODO: Implement standings update logic
    return False
```

## Database Schema (SQLite)

### tournaments Table
```sql
CREATE TABLE tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topdeck_tournament_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    status TEXT DEFAULT 'pending',  -- pending, ongoing, completed, cancelled
    host_user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### players Table
```sql
CREATE TABLE players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_chat_id INTEGER NOT NULL,
    tournament_id INTEGER REFERENCES tournaments(id),
    player_name TEXT NOT NULL,
    team TEXT,
    rank INTEGER,
    points INTEGER DEFAULT 0,
    UNIQUE(telegram_chat_id, tournament_id)
);
```

### standings Table
```sql
CREATE TABLE standings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER REFERENCES tournaments(id),
    position INTEGER NOT NULL,
    team_name TEXT NOT NULL,
    points INTEGER DEFAULT 0,
    games_played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### history_archive Table
```sql
CREATE TABLE history_archive (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER UNIQUE REFERENCES tournaments(id),
    completion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_participants INTEGER,
    winner_team TEXT,
    notes TEXT
);
```

## Future Roadmap

- [ ] **Implement point logic** - Complete `src/points.py` with actual calculation rules
- [ ] **Add admin commands** - Create `/admin-*` command handlers for tournament management
- [ ] **Enhance caching** - Implement Redis/SQLite caching for API responses
- [ ] **Webhook support** - Replace polling with TopDeck webhooks when available
- [ ] **Advanced analytics** - Tournament history, team performance tracking
- [ ] **Multi-team support** - Track multiple teams across different Telegram chats
- [ ] **Export data** - Export standings to CSV/Excel formats

## Troubleshooting

### Bot doesn't respond
- Verify `BOT_TOKEN` is correct in `.env`
- Check internet connection
- Review logs (check terminal output or log file if configured)

### API errors
- Verify TopDeck credentials in `.env`
- Ensure API endpoint (`TOPDECK_API_URL`) is accessible
- Check for rate limits (wait 60 seconds between requests)

### Database issues
- Ensure `data/` directory has write permissions
- If database file is corrupted, reinitialize: delete `data/tournaments.db` and restart bot

### Rate limiting from TopDeck API
- The bot automatically waits on rate limit errors
- You can increase `TOPDECK_POLL_INTERVAL` in `.env` to reduce API calls

## Security Notes

- Never commit `.env` file to Git (it's in `.gitignore`)
- Rotate TopDeck API credentials periodically
- Use HTTPS only for API connections

## License

This project is for internal use within your organization.

---

**Need help?** Check the [DEVELOPMENT_GUIDE.md](/c:/Users/jdelv/Documents/python/telegrambot/DEVELOPMENT_GUIDE.md) for detailed setup instructions and troubleshooting tips.
