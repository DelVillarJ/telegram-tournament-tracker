# User guide

The bot uses the TopDeck account configured by `TOPDECK_API_KEY`. Send `/start`
or `/help` to the bot for its current command list.

## Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and command overview. |
| `/status` | Lists tournaments returned by the configured TopDeck account. |
| `/points` | Shows all players' cumulative 2026 Poyo League points. |
| `/bonus <signed points> <player name or TopDeck ID>` | Applies a manual adjustment; admin-only. |
| `/admin <add|remove> <@username or Telegram user ID>` | Adds or removes a bot admin; admin-only. |
| `/setdefaultchannel` | Sets this group as the default destination for new TopDeck tournaments; admin-only. |
| `/assignchannel <TopDeck tournament ID> [chat ID or @channel]` | Assigns the result destination; admin-only. |
| `/help` | Lists commands. |

## League scoring

- Events with 8 or more standings entries use monthly scoring: places 1–10 earn
  25, 18, 15, 12, 10, 8, 6, 4, 2, and 1 point, respectively.
- Events with 7 or fewer standings entries use weekly scoring: places 1–5 earn
  6, 4, 3, 2, and 1 point, respectively.
- Monthly events award an extra point to players with no losses in non-bracket
  rounds. Draws are not losses; bracket results are not considered.
- Bonus adjustments are added to the cumulative league total and may be
  negative. Each adjustment is stored separately for auditability.

## Manual point adjustments

Admins can use `/bonus` and manage the persistent admin list with `/admin`.
Use `/admin add @username` or `/admin add <Telegram user ID>` to grant access,
and `/admin remove` with the same target format to revoke it. The last remaining
admin cannot be removed. `BONUS_ADMIN_IDS`, `BONUS_ADMIN_USERNAMES`, and
`@poyotcg` seed the list when it is first created; later changes are stored in
SQLite and take effect immediately.

Examples:

```text
/bonus +5 Angel Fuentes
/bonus -3 Angel Fuentes
```

The player must match a 2026 league entry by exact name (case-insensitive) or
TopDeck player ID. The bot responds with the applied delta, net bonus, and
updated league total. Unknown or ambiguous names are rejected.

## TopDeck completion webhooks

The bot defaults to the configured league channel
(`TOPDECK_DEFAULT_CHAT_ID`, default `-1004340474920`) for tournaments without an
explicit destination and routes all results there, including completion
events already waiting for a retry. The configured destination takes
precedence over stored per-tournament assignments. To change the destination,
update `TOPDECK_DEFAULT_CHAT_ID` in `.env` and recreate the service. When no
configured default is set, `/assignchannel <TopDeck tournament ID>` in a group
or `/assignchannel <TopDeck tournament ID> @channelusername` from an admin chat
can set a tournament-specific destination.

Configure a TopDeck webhook endpoint at
`https://<your-public-host>/webhooks/topdeck`, subscribe it to
`tournament.finished`, and set its
`whsec_...` signing secret as `TOPDECK_WEBHOOK_SECRET`. TopDeck calls the
check-in event `tournament.checkin_started`; it can associate a tournament
early if subscribed, but it is not required when the bot has a default channel.
The receiver fetches current rounds and stores final results in SQLite. Since
TopDeck does not record the semifinal losers'
third-place match, it posts two candidate buttons to the assigned destination;
a bot admin selects third place, and the bot stores the corrected league
standings and posts the final results.

TopDeck only delivers to publicly resolvable HTTPS URLs. For homelab
deployments, route HTTPS through a reverse proxy/tunnel to the host-bound
webhook port. The default Compose binding is `127.0.0.1:8080`; set
`WEBHOOK_BIND_ADDRESS` only if ingress requires a different host binding.

## Data and support

Tournament standings and manual point adjustments are stored in SQLite at
`DATABASE_PATH` (default `data/tournaments.db`). In Docker, the host `data/`
directory is mounted at `/app/data`.

For setup, see the [quick start](quickstart.md); for local development, see the
[development guide](development-guide.md).
