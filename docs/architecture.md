# Architecture overview

## Runtime

`python -m src.main` creates the database manager and TopDeck service, registers
`aiogram` message handlers, and starts Telegram long polling. `/status` calls
the authenticated TopDeck account-tournaments endpoint. `/points` reads the
stored 2026 league standings from SQLite. `/bonus` appends an authorized,
auditable adjustment to the same player's cumulative score.

```text
Telegram
   │ long polling / commands
   ▼
aiogram handlers ─────── TopDeckService ─────── TopDeck Tournaments V2 API
   │                           │
   │ /bonus                    │ /points
   ▼                           ▼
BonusAdjustment            Standings + Tournament
   └─────────────── SQLite ────────────────┘
```

## League score data

- `Tournament` stores TopDeck event identity, name, participant count, and
  start/end dates.
- `Standings` stores event rank, TopDeck player ID, earned points, wins, and
  the monthly undefeated bonus.
- `BonusAdjustment` stores each manual signed point delta with player identity,
  acting Telegram user, and creation time.
- `Notification` stores notification history.

The leaderboard groups tournament rows by TopDeck player ID and year, sums
earned points, and adds the player's manual bonus total. It is ordered by the
resulting score.

## Scoring

An event with at least eight standings rows uses monthly place points; smaller
events use weekly place points. Monthly undefeated bonus eligibility is
computed from completed rounds numbered up to TopDeck's `swissNum`, so
elimination bracket outcomes are excluded. A draw does not count as a loss. A
round without a completed result does not qualify its participants as
undefeated.

## Configuration and persistence

Configuration is read from environment variables and `.env` for local
development. Docker Compose passes `.env` values into the application and
mounts `./data` at `/app/data`. The bot uses Telegram long polling, so no local
HTTP health endpoint or exposed application port is required.

See the [user guide](user-guide.md) for commands and
[development guide](development-guide.md) for test and deployment commands.
