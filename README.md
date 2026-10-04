# Telegram Bot - TopDeck Tournament Tracker
A Python-based Telegram bot that integrates with the TopDeck API to track tournaments, notify when they finish, and update points standings for your group.

## Features

- 🤖 **Telegram Integration**: Full bot functionality using python-telegram-bot
- 🏆 **Tournament Tracking**: Monitor all tournaments hosted by specific users on TopDeck
- 🔔 **Notifications**: Automatic notifications when tournaments complete
- 📊 **Points System**: Track and update standings (logic will be implemented later)
- 💾 **Local Persistence**: SQLite database for storing tournament data
- ⚙️ **Flexible Configuration**: Environment-based configuration with secure secret handling
- 🐳 **Docker Ready**: Optional containerization support

## Project Structure

```
telegrambot/
├── README.md                    # This file
├── DEVELOPMENT_GUIDE.md         # Detailed setup and development guide
├── CODE_FLOW_DIAGRAM.mmd        # Mermaid diagram of bot architecture
├── .env.example                  # Environment variable template
├── .gitignore                    # Git ignore rules
│
├── src/
│   ├── __init__.py
│   ├── config.py                # Configuration loader
│   ├── database.py              # Database schema and queries
│   ├── bot.py                   # Main bot initialization and commands
│   ├── topdeck_api.py           # TopDeck API integration
│   ├── tournament_tracker.py    # Tournament detection and tracking
│   ├── points.py                # Point system logic (TODO)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py           # Logging configuration
│       └── validators.py        # Input validation helpers
│
└── tests/
    ├── __init__.py
    ├── test_tournament_tracker.py
    ├── test_points.py
    └── test_database.py
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- pip or poetry for package management
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
   source venv/bin/activate  # On Linux/Mac
   # or
   venv\Scripts\activate     # On Windows
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

# TopDeck API Configuration  
TOPDECK_API_URL=https://api.topdeck.com
TOPDECK_CLIENT_ID=your_client_id
TOPDECK_CLIENT_SECRET=your_client_secret
TOPDECK_REDIRECT_URI=http://localhost:8000/callback

# Tournament Tracking Configuration
TARGET_USER_ID=user_id_to_track  # User whose tournaments to track
TOPDECK_POLL_INTERVAL=60         # Seconds between API polling

# Bot Behavior
NOTIFY_ON_COMPLETE=true
AUTO_UPDATE_STANDINGS=true
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

### Using Process Manager (Optional)

```bash
# Install supervisor or systemd for production
supervisord -c supervisor.conf
```

## Available Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize the bot and show help |
| `/status` | Show current tournament status |
| `/standings` | Display points standings |
| `/tournaments` | List all tracked tournaments |
| `/add-tournament <tournament_id>` | Manually add a tournament |
| `/remove-tournament <tournament_id>` | Remove from tracking |
| `/help` | Show command list |

## Code Flow Explanation

1. **Initialization**: Bot loads configuration, connects to Telegram and TopDeck API
2. **Command Handlers**: Telegram commands trigger appropriate handlers
3. **Background Polling**: Periodic checks of TopDeck API for tournament updates
4. **Completion Detection**: Tournament status changes trigger notifications
5. **Points Update**: (TODO) Logic calculates points and updates database

See [CODE_FLOW_DIAGRAM.mmd](/c:/Users/jdelv/Documents/python/telegrambot/CODE_FLOW_DIAGRAM.mmd) for detailed architecture.

## Point System (TODO)

The point system logic will be implemented in `src/points.py`. Currently, this file contains placeholder functions:

```python
def calculate_tournament_points(tournament, team):
    """Calculate points earned by a team in a tournament."""
    # TODO: Implement point logic here
    pass

def update_standings(tournament_result):
    """Update standings based on tournament results."""
    # TODO: Implement standings update logic
    pass
```

## Database Schema

### Tournaments Table
```sql
CREATE TABLE tournaments (
    id INTEGER PRIMARY KEY,
    topdeck_tournament_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    status TEXT,  -- ongoing, completed, cancelled
    host_user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Players Table
```sql
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    telegram_chat_id INTEGER NOT NULL,
    tournament_id INTEGER REFERENCES tournaments(id),
    player_name TEXT NOT NULL,
    team TEXT,
    rank INTEGER,
    points INTEGER DEFAULT 0,
    UNIQUE(telegram_chat_id, tournament_id)
);
```

### Standings Table
```sql
CREATE TABLE standings (
    id INTEGER PRIMARY KEY,
    tournament_id INTEGER REFERENCES tournaments(id),
    position INTEGER NOT NULL,
    team_name TEXT NOT NULL,
    points INTEGER DEFAULT 0,
    games_played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    goal_for INTEGER DEFAULT 0,
    goal_against INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Future Roadmap

- [ ] **Admin Commands**: Add admin-only commands for managing tracked tournaments
- [ ] **Caching**: Implement Redis/SQLite caching for API responses
- [ ] **Webhook Support**: Replace polling with TopDeck webhooks when available
- [ ] **Advanced Analytics**: Tournament history, team performance tracking
- [ ] **Custom Point Systems**: Allow configuration of point rules per tournament type
- [ ] **Multi-team Support**: Track multiple teams across different Telegram chats
- [ ] **Web Dashboard**: Optional web interface for viewing standings
- [ ] **Export Data**: Export standings to CSV/Excel formats

## Troubleshooting

### Bot doesn't respond
- Verify BOT_TOKEN is correct in `.env`
- Check internet connection
- Review logs in the terminal where bot is running

### API errors
- Verify TopDeck credentials
- Check that API endpoint is accessible
- Review error messages in logs

### Database issues
- Ensure SQLite file has write permissions
- Run database migration if schema changes

## License

This project is for internal use within your organization.

---

**Need help?** Check the [DEVELOPMENT_GUIDE.md](/c:/Users/jdelv/Documents/python/telegrambot/DEVELOPMENT_GUIDE.md) for detailed setup instructions and troubleshooting tips.