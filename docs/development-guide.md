# Development guide

## Environment

Use Python 3.11+ and install the repository dependencies into a virtual
environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `BOT_TOKEN` and `TOPDECK_API_KEY` in `.env` before starting the bot. The
runtime entrypoint is `python -m src.main`; it loads settings, creates or
migrates the SQLite schema, registers the `aiogram` handlers, and starts
Telegram long polling.

## Tests

Run the full test suite from the repository root:

```powershell
python -m pytest
```

Useful focused suites:

```powershell
python -m pytest tests/test_points_calculator.py
python -m pytest tests/test_topdeck.py tests/test_topdeck_api.py
python -m pytest tests/test_handlers.py
```

Tests use temporary SQLite databases and mocked API responses; live TopDeck
credentials are not required for the unit tests.

## Code map

- `src/handlers/__init__.py` registers bot commands and injects services.
- `src/services/topdeck.py` reads the league leaderboard and records signed
  bonus adjustments.
- `src/services/points_calculator.py` applies the monthly/weekly scoring rules
  and derives undefeated players from TopDeck Swiss-round results.
- `src/topdeck/_api.py` implements requests to the TopDeck Tournaments V2 API.
- `src/models/` contains SQLAlchemy models and startup schema migrations.
- `migrations/init.py` initializes the configured database.

## Database and deployment

The SQLAlchemy models define the runtime schema. `DatabaseManager.create_all()`
creates missing tables and adds supported columns to existing standings tables.
For local work, the default SQLite path is `data/tournaments.db`. Docker
overrides it with `/app/data/tournaments.db` and bind-mounts the host `data/`
directory.

Run or recreate the Docker service with:

```powershell
docker compose --env-file .env up --detach --build --force-recreate
```

The bot uses long polling and does not serve an HTTP endpoint. Follow logs with
`docker compose logs --follow telegram-bot`.

See the [architecture overview](architecture.md), [quick start](quickstart.md),
and [user guide](user-guide.md) for the related behavior and commands.
