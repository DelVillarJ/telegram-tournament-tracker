# Architecture Overview

This document describes the architecture of the Telegram Bot for TopDeck Tournament Tracking.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      TELEGRAM BOT                           │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Command      │  │ Callback     │  │ Notification  │      │
│  │ Handlers     │  │ Handlers     │  │ Service       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                     │         │                              │
│              ┌──────┴───┐    ┌┴──────────────┐             │
│              │   Router │    │ TopDeck       │             │
│              └──────────┘    │ Service       │             │
│                              └───────────────┘             │
├─────────────────────────────────────────────────────────────┤
│                      DATABASE                               │
│              SQLite / PostgreSQL                            │
├─────────────────────────────────────────────────────────────┤
│                      EXTERNAL API                           │
│                  TopDeck API                                │
└─────────────────────────────────────────────────────────────┘
```

## Component Diagram

```
                    ┌──────────────┐
                    │  Telegram    │
                    │   Bot        │
                    │  (aiogram)   │
                    └──────┬───────┘
                           │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Tournament  │    │   Standings │    │ Notifications│
│ Service     │    │  Manager    │    │   Queue      │
└─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Models    │    │  Database   │    │ Telegram     │
│ (Pydantic)  │    │  Repository │    │  Groups      │
└─────────────┘    └─────────────┘    └─────────────┘
                           │
                    ┌──────┴───────┐
                    │ TopDeck API  │
                    └──────────────┘
```

## Data Flow

### Tournament Tracking Flow

1. **Bot receives command** (`/status`) or triggers via poll interval
2. **Command handler** routes to `TournamentService`
3. **TopDeck Service** queries TopDeck API for active tournaments
4. **Data is cached** and returned to handlers
5. **Handlers format response** for Telegram users

### Tournament Completion Flow

1. **Polling service** detects tournament completion via TopDeck API
2. **Completion event** triggers `NotificationService.notify_tournament_complete()`
3. **Notifications sent** to configured groups/channels
4. **Event logged** to database with timestamp

### Standings Update Flow

1. **Scheduled job** runs every N seconds (configurable)
2. **Fetch latest standings** from TopDeck API
3. **Compare with cached data** for changes
4. **Send update notification** if changed
5. **Update cache** and database

## Database Schema

### Tables Overview

```
┌───────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ tournaments   │    │  standings      │    │ notifications    │
├───────────────┤    ├─────────────────┤    ├─────────────────┤
│ id            │    │ id              │    │ id               │
│ tournament_id │───▶│ tournament_id   │───▶│ tournament_id   │
│ name          │    │ player_name     │    │ group_id         │
│ status        │    │ points          │    │ message          │
│ participant_c │    │ wins            │    │ sent_at          │
│ ...           │    │ matches_played  │    │ success          │
└───────────────┘    │ tournament_id   │    │ error_message    │
                     └─────────────────┘    └─────────────────┘
                              ▲                   ▲
                              │                   │
                         (has_many)          (has_many)
```

## Service Layer

### TopDeckService

- `get_active_tournaments()` - Fetch active tournaments
- `get_tournament_details(tourney_id)` - Get single tournament info
- `get_standings(tournament_id)` - Get standings data
- `check_tournament_status(id)` - Check if completed
- `sync_tournament_data(id)` - Sync local data with API

### NotificationService

- `send_to_groups(message, group_ids)` - Send to multiple groups
- `notify_tournament_complete()` - Notify when finished
- `notify_standings_updated()` - Send standings update
- `notify_new_tournament()` - Announce new tournaments

## Handler Registration

Handlers are registered in `src/handlers/__init__.py`:

```python
router = Router()

@router.message(Command("start"))
async def start(message): ...

@router.message(Command("status"))
async def status(message, topdeck_service): ...
```

## Extension Points

To add new functionality:

1. **New command**: Add handler in `src/handlers/__init__.py`
2. **New endpoint**: Create service method in `src/services/`
3. **New model**: Add to `src/models/schemas.py` or database
4. **New config**: Add to `.env.template` with defaults

## Deployment Considerations

- **Database**: SQLite for dev, PostgreSQL for production
- **Caching**: Consider Redis for high-frequency updates
- **Rate limiting**: Respect TopDeck API rate limits
- **Webhooks**: Use `webhook_url` in @BotFather instead of polling
- **SSL**: Always use HTTPS for webhook endpoints

## Monitoring & Logging

Logs are written to:
- Console (default)
- File (if `LOG_FILE` configured)

Log levels: DEBUG, INFO, WARNING, ERROR

Key metrics to track:
- API call success rate
- Notification delivery time
- Tournament completion latency
- User command frequency

## Security Considerations

- Bot token never logged or committed
- Environment variables for secrets
- Rate limiting on API calls
- Input validation on all commands
- Group ID whitelist for notifications
