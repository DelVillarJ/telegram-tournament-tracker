"""Signed TopDeck webhook receiver and tournament-finish workflow."""

import asyncio
import hashlib
import hmac
import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict

from aiohttp import web
from aiogram import Bot, types

from src.models.database import (
    DefaultTournamentChannel,
    Standings,
    TopDeckWebhookEvent,
    Tournament,
    TournamentChannel,
    TournamentCompletionReview,
)
from src.models.database_manager import DatabaseManager
from src.services.points_calculator import calculate_points, get_undefeated_player_ids
from src.topdeck._api import TopDeckAPI

logger = logging.getLogger(__name__)


class TournamentReviewSummary(TypedDict):
    token: str
    chat_id: str
    status: str
    third_place_id: str | None


def verify_topdeck_signature(raw_body: bytes, header: str, secret: str) -> bool:
    """Verify TopDeck's HMAC-SHA256 signature over timestamp and raw bytes."""
    if not header or not secret:
        return False

    fields: dict[str, str] = {}
    for part in header.split(","):
        key, separator, value = part.strip().partition("=")
        if separator and key in {"t", "v1"}:
            fields[key] = value

    timestamp = fields.get("t", "")
    signature = fields.get("v1", "")
    if not timestamp.isdecimal() or not re.fullmatch(r"[0-9a-fA-F]{64}", signature):
        return False

    signed_content = timestamp.encode("ascii") + b"." + raw_body
    expected = hmac.new(
        secret.encode("utf-8"),
        signed_content,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature.lower(), expected)


def _as_position(value: Any) -> int | None:
    try:
        position = int(value)
    except (TypeError, ValueError):
        return None
    return position if position > 0 else None


def _normalized_standings(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("TopDeck tournament-finished event has no standings list.")

    standings: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        player_id = row.get("id")
        player_name = row.get("name") or row.get("display_name")
        if not isinstance(player_id, str) or not player_id.strip():
            continue
        if not isinstance(player_name, str) or not player_name.strip():
            continue
        standings.append(
            {
                "id": player_id,
                "name": player_name,
                "position": _as_position(
                    row.get("standing", row.get("rank", row.get("position")))
                )
                or index,
                "wins": _as_position(row.get("wins")) or 0,
                "draws": _as_position(row.get("draws")) or 0,
                "losses": _as_position(row.get("losses")) or 0,
            }
        )

    if not standings:
        raise ValueError("TopDeck tournament-finished event has no valid players.")
    return standings


def _semifinal_losers(tournament: dict[str, Any]) -> list[dict[str, str]]:
    rounds = tournament.get("rounds")
    if not isinstance(rounds, list):
        return []

    for round_data in rounds:
        if not isinstance(round_data, dict):
            continue
        label = str(
            round_data.get("roundLabel", round_data.get("round", ""))
        ).casefold()
        if not any(term in label for term in ("top 4", "semifinal", "semi-final")):
            continue

        tables = round_data.get("tables")
        if not isinstance(tables, list):
            continue
        losers: dict[str, str] = {}
        for table in tables:
            if not isinstance(table, dict):
                continue
            players = table.get("players")
            winner_id = table.get("winner_id")
            if not isinstance(players, list) or not isinstance(winner_id, str):
                continue
            for player in players:
                if not isinstance(player, dict):
                    continue
                player_id = player.get("id")
                player_name = player.get("name")
                if (
                    isinstance(player_id, str)
                    and player_id != winner_id
                    and isinstance(player_name, str)
                ):
                    losers[player_id] = player_name
        if len(losers) == 2:
            return [
                {"id": player_id, "name": name}
                for player_id, name in losers.items()
            ]
    return []


def _confirmation_candidates(
    standings: list[dict[str, Any]],
    tournament: dict[str, Any],
) -> list[dict[str, str]]:
    candidates = _semifinal_losers(tournament)
    standings_by_id = {player["id"]: player for player in standings}
    if len(candidates) == 2 and all(
        candidate["id"] in standings_by_id for candidate in candidates
    ):
        return [
            {
                "id": candidate["id"],
                "name": standings_by_id[candidate["id"]]["name"],
            }
            for candidate in candidates
        ]

    candidates = [
        {"id": row["id"], "name": row["name"]}
        for row in standings
        if row["position"] in {3, 4}
    ]
    if len(candidates) == 2:
        return candidates

    ordered = sorted(standings, key=lambda row: row["position"])
    fallback = ordered[2:4]
    if len(fallback) == 2 and len({player["id"] for player in fallback}) == 2:
        return [{"id": row["id"], "name": row["name"]} for row in fallback]
    raise ValueError("Could not identify both semifinal losers for third-place review.")


def _event_datetime(value: Any, fallback_ms: Any) -> datetime:
    timestamp_ms = value if isinstance(value, (int, float)) else fallback_ms
    if not isinstance(timestamp_ms, (int, float)):
        return datetime.now(timezone.utc).replace(tzinfo=None)
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).replace(
        tzinfo=None
    )


class TopDeckWebhookService:
    """Accept, deduplicate, and process TopDeck's tournament webhook events."""

    def __init__(
        self,
        database_manager: DatabaseManager,
        bot: Bot,
        api_client: TopDeckAPI,
        signing_secret: str,
        default_chat_id: str = "",
    ) -> None:
        self.database_manager = database_manager
        self.bot = bot
        self.api_client = api_client
        self.signing_secret = signing_secret
        self.default_chat_id = default_chat_id.strip()

    def create_app(self) -> web.Application:
        app = web.Application(client_max_size=1024 * 1024)
        app.router.add_get("/health", self.health)
        app.router.add_post("/webhooks/topdeck", self.receive_event)
        return app

    async def health(self, _request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def receive_event(self, _request: web.Request) -> web.Response:
        raw_body = await _request.read()
        signature = _request.headers.get("X-TopDeck-Signature", "")
        if not verify_topdeck_signature(raw_body, signature, self.signing_secret):
            return web.Response(status=401, text="invalid signature")

        try:
            event = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return web.Response(status=400, text="invalid JSON")
        if not isinstance(event, dict):
            return web.Response(status=400, text="invalid event envelope")

        event_id = event.get("id")
        event_type = event.get("type")
        tournament_id = event.get("tid")
        if (
            not isinstance(event_id, str)
            or not event_id.strip()
            or not isinstance(event_type, str)
            or not event_type.strip()
            or (
                tournament_id is not None
                and not isinstance(tournament_id, str)
            )
        ):
            return web.Response(status=400, text="invalid event envelope")

        header_event_id = _request.headers.get("X-TopDeck-Event-Id")
        header_event_type = _request.headers.get("X-TopDeck-Event")
        if (
            (header_event_id and header_event_id != event_id)
            or (header_event_type and header_event_type != event_type)
        ):
            return web.Response(status=400, text="event headers do not match body")

        try:
            await asyncio.to_thread(self._enqueue_event, event)
        except Exception:
            logger.exception("Could not persist TopDeck webhook event %s", event_id)
            return web.Response(status=503, text="event persistence failed")
        return web.json_response({"received": True})

    def _enqueue_event(self, event: dict[str, Any]) -> None:
        with self.database_manager.get_session() as session:
            if session.get(TopDeckWebhookEvent, event["id"]) is not None:
                return
            session.add(
                TopDeckWebhookEvent(
                    event_id=event["id"],
                    event_type=event["type"],
                    tournament_id=event.get("tid"),
                    payload=json.dumps(event, separators=(",", ":")),
                    status="pending",
                    next_attempt_at=datetime.utcnow(),
                )
            )
            session.commit()

    async def run_worker(self) -> None:
        await asyncio.to_thread(self._recover_interrupted_events)
        while True:
            event_record = await asyncio.to_thread(self._claim_next_event)
            if event_record is None:
                await asyncio.sleep(1)
                continue

            try:
                event = json.loads(event_record["payload"])
                await self.process_event(event)
            except Exception as error:
                logger.exception(
                    "TopDeck event processing failed for event %s",
                    event_record["event_id"],
                )
                await asyncio.to_thread(
                    self._retry_event,
                    event_record["event_id"],
                    event_record["attempts"],
                    str(error),
                )
            else:
                await asyncio.to_thread(
                    self._complete_event,
                    event_record["event_id"],
                )

    def _recover_interrupted_events(self) -> None:
        with self.database_manager.get_session() as session:
            session.query(TopDeckWebhookEvent).filter(
                TopDeckWebhookEvent.status == "processing"
            ).update(
                {
                    TopDeckWebhookEvent.status: "pending",
                    TopDeckWebhookEvent.next_attempt_at: datetime.utcnow(),
                },
                synchronize_session=False,
            )
            session.commit()

    def _claim_next_event(self) -> dict[str, Any] | None:
        now = datetime.utcnow()
        with self.database_manager.get_session() as session:
            event = (
                session.query(TopDeckWebhookEvent)
                .filter(
                    TopDeckWebhookEvent.status == "pending",
                    TopDeckWebhookEvent.next_attempt_at <= now,
                )
                .order_by(TopDeckWebhookEvent.received_at)
                .first()
            )
            if event is None:
                return None
            event.status = "processing"
            event.attempts += 1
            result = {
                "event_id": event.event_id,
                "payload": event.payload,
                "attempts": event.attempts,
            }
            session.commit()
            return result

    def _retry_event(self, event_id: str, attempts: int, error: str) -> None:
        delay = min(30 * (2 ** min(attempts - 1, 5)), 600)
        with self.database_manager.get_session() as session:
            event = session.get(TopDeckWebhookEvent, event_id)
            if event is None:
                return
            event.status = "pending"
            event.next_attempt_at = datetime.utcnow() + timedelta(seconds=delay)
            event.last_error = error[:2000]
            session.commit()

    def _complete_event(self, event_id: str) -> None:
        with self.database_manager.get_session() as session:
            event = session.get(TopDeckWebhookEvent, event_id)
            if event is not None:
                event.status = "done"
                event.last_error = None
                session.commit()

    async def process_event(self, event: dict[str, Any]) -> None:
        if event.get("type") == "tournament.checkin_started":
            tournament_id = event.get("tid")
            if not isinstance(tournament_id, str) or not tournament_id.strip():
                raise ValueError("Check-in event is missing its tournament ID.")
            await asyncio.to_thread(
                self._assign_default_channel,
                tournament_id,
            )
            return

        if event.get("type") != "tournament.finished":
            return
        tournament_id = event.get("tid")
        data = event.get("data")
        if not isinstance(tournament_id, str) or not tournament_id.strip():
            raise ValueError("Finished event is missing its tournament ID.")
        if not isinstance(data, dict):
            raise ValueError("Finished event is missing its result data.")

        standings = _normalized_standings(data.get("standings"))
        tournament_name = (
            event.get("tournament", {}).get("name")
            if isinstance(event.get("tournament"), dict)
            else None
        ) or tournament_id
        participant_count = data.get("participantCount")
        if not isinstance(participant_count, int) or participant_count < 1:
            participant_count = len(standings)
        ended_at = _event_datetime(data.get("endedAt"), event.get("created"))

        if participant_count < 8:
            result = await asyncio.to_thread(
                self._save_weekly_results,
                tournament_id,
                tournament_name,
                standings,
                participant_count,
                ended_at,
            )
            await self.bot.send_message(
                chat_id=result["chat_id"],
                text=(
                    f"✅ Weekly event {tournament_name} finished "
                    f"({participant_count} players). Results imported and "
                    "league standings updated."
                ),
            )
            return

        tournament_rows = await asyncio.to_thread(
            self.api_client.search_tournaments,
            tid=tournament_id,
            rounds=True,
            tables=["table", "players", "winner", "status"],
            players=["name", "id"],
        )
        latest_tournament = next(
            (
                row
                for row in tournament_rows
                if row.get("TID", row.get("id")) == tournament_id
            ),
            None,
        )
        if latest_tournament is None:
            raise ValueError(
                f"TopDeck did not return current round data for {tournament_id}."
            )
        candidates = _confirmation_candidates(standings, latest_tournament)
        undefeated_ids = get_undefeated_player_ids(latest_tournament)

        review = await asyncio.to_thread(
            self._save_pending_review,
            tournament_id,
            tournament_name,
            standings,
            candidates,
            sorted(undefeated_ids),
            participant_count,
            ended_at,
        )
        if review["status"] == "confirmed":
            selected_index = next(
                (
                    index
                    for index, candidate in enumerate(candidates)
                    if candidate["id"] == review.get("third_place_id")
                ),
                0,
            )
            await self.confirm_third_place(
                review["token"],
                selected_index,
                "webhook-retry",
            )
            return
        await self.bot.send_message(
            chat_id=review["chat_id"],
            text=(
                f"🏁 {tournament_name} has finished. "
                "TopDeck does not record a third-place match result. "
                "An admin should select which semifinalist finished third:"
            ),
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text=candidate["name"],
                            callback_data=f"third:{review['token']}:{index}",
                        )
                    ]
                    for index, candidate in enumerate(candidates)
                ]
            ),
        )

    def _assign_default_channel(self, tournament_id: str) -> None:
        with self.database_manager.get_session() as session:
            with session.begin():
                self._ensure_tournament_channel(session, tournament_id)

    def _ensure_tournament_channel(
        self,
        session,
        tournament_id: str,
    ) -> TournamentChannel:
        channel = session.get(TournamentChannel, tournament_id)
        if self.default_chat_id:
            chat_id = self.default_chat_id
            assigned_by = "configuration"
            if channel is None:
                channel = TournamentChannel(
                    tournament_id=tournament_id,
                    chat_id=chat_id,
                    assigned_by=assigned_by,
                )
                session.add(channel)
            else:
                channel.chat_id = chat_id
                channel.assigned_by = assigned_by
            session.flush()
            return channel

        if channel is not None:
            return channel

        default_channel = session.get(DefaultTournamentChannel, "default")
        if default_channel is not None:
            chat_id = default_channel.chat_id
            assigned_by = default_channel.assigned_by
        else:
            raise ValueError(
                "No Telegram destination is assigned to tournament "
                f"{tournament_id}; configure TOPDECK_DEFAULT_CHAT_ID, "
                "run /setdefaultchannel in the target group, or use "
                "/assignchannel."
            )

        channel = TournamentChannel(
            tournament_id=tournament_id,
            chat_id=chat_id,
            assigned_by=assigned_by,
        )
        session.add(channel)
        session.flush()
        logger.info(
            "Assigned tournament %s to its default Telegram destination",
            tournament_id,
        )
        return channel

    def _save_weekly_results(
        self,
        tournament_id: str,
        tournament_name: str,
        standings: list[dict[str, Any]],
        participant_count: int,
        ended_at: datetime,
    ) -> dict[str, str]:
        with self.database_manager.get_session() as session:
            with session.begin():
                channel = self._ensure_tournament_channel(session, tournament_id)

                tournament = (
                    session.query(Tournament)
                    .filter_by(tournament_id=tournament_id)
                    .one_or_none()
                )
                if tournament is None:
                    tournament = Tournament(
                        tournament_id=tournament_id,
                        name=tournament_name,
                    )
                    session.add(tournament)
                tournament.name = tournament_name
                tournament.status = "completed"
                tournament.participant_count = participant_count
                tournament.end_time = ended_at
                if tournament.start_time is None:
                    tournament.start_time = ended_at

                self._write_standings(
                    session,
                    tournament_id,
                    standings,
                    participant_count,
                    set(),
                )
                return {"chat_id": channel.chat_id}

    def _save_pending_review(
        self,
        tournament_id: str,
        tournament_name: str,
        standings: list[dict[str, Any]],
        candidates: list[dict[str, str]],
        undefeated_ids: list[str],
        participant_count: int,
        ended_at: datetime,
    ) -> TournamentReviewSummary:
        with self.database_manager.get_session() as session:
            with session.begin():
                channel = self._ensure_tournament_channel(session, tournament_id)

                tournament = (
                    session.query(Tournament)
                    .filter_by(tournament_id=tournament_id)
                    .one_or_none()
                )
                if tournament is None:
                    tournament = Tournament(
                        tournament_id=tournament_id,
                        name=tournament_name,
                    )
                    session.add(tournament)
                tournament.name = tournament_name
                tournament.status = "completed"
                tournament.participant_count = participant_count
                tournament.end_time = ended_at
                if tournament.start_time is None:
                    tournament.start_time = ended_at

                review = session.get(TournamentCompletionReview, tournament_id)
                if review is None:
                    review = TournamentCompletionReview(
                        tournament_id=tournament_id,
                        review_token=uuid.uuid4().hex,
                        chat_id=channel.chat_id,
                        tournament_name=tournament_name,
                        standings=json.dumps(standings),
                        candidates=json.dumps(candidates),
                        undefeated_player_ids=json.dumps(undefeated_ids),
                        participant_count=participant_count,
                        ended_at=ended_at,
                        status="pending",
                    )
                    session.add(review)
                elif review.status == "pending":
                    review.chat_id = channel.chat_id
                    review.tournament_name = tournament_name
                    review.standings = json.dumps(standings)
                    review.candidates = json.dumps(candidates)
                    review.undefeated_player_ids = json.dumps(undefeated_ids)
                    review.participant_count = participant_count
                    review.ended_at = ended_at

                review_token = review.review_token
                chat_id = review.chat_id
                review_status = review.status
                third_place_id = review.third_place_id

                if review_status == "pending":
                    self._write_standings(
                        session,
                        tournament_id,
                        standings,
                        participant_count,
                        set(undefeated_ids),
                    )

            return {
                "token": review_token,
                "chat_id": chat_id,
                "status": review_status,
                "third_place_id": third_place_id,
            }

    @staticmethod
    def _write_standings(
        session: Any,
        tournament_id: str,
        standings: list[dict[str, Any]],
        participant_count: int,
        undefeated_ids: set[str],
        third_place_id: str | None = None,
        candidates: list[dict[str, str]] | None = None,
    ) -> None:
        positions = {row["id"]: row["position"] for row in standings}
        if third_place_id is not None and candidates is not None:
            positions[third_place_id] = 3
            fourth_place = next(
                candidate["id"]
                for candidate in candidates
                if candidate["id"] != third_place_id
            )
            positions[fourth_place] = 4

        session.query(Standings).filter(
            Standings.tournament_id == tournament_id
        ).delete(synchronize_session=False)
        for row in standings:
            position = positions[row["id"]]
            session.add(
                Standings(
                    tournament_id=tournament_id,
                    player_id=row["id"],
                    player_name=row["name"],
                    position=position,
                    points=calculate_points(
                        position,
                        participant_count,
                        undefeated=row["id"] in undefeated_ids,
                    ),
                    wins=row["wins"],
                    matches_played=row["wins"] + row["draws"] + row["losses"],
                )
            )

    async def confirm_third_place(
        self,
        token: str,
        candidate_index: int,
        confirmer_id: str,
    ) -> str:
        result = await asyncio.to_thread(
            self._confirm_third_place,
            token,
            candidate_index,
            confirmer_id,
        )
        if result["status"] == "pending":
            return "This third-place review is still pending."
        if result["status"] == "missing":
            return "This third-place review is no longer available."
        if result["status"] == "confirmed":
            await self._send_final_results(result)
            return f"Third place confirmed as {result['third_name']}."
        return "This review has already been completed."

    def _confirm_third_place(
        self,
        token: str,
        candidate_index: int,
        confirmer_id: str,
    ) -> dict[str, Any]:
        with self.database_manager.get_session() as session:
            with session.begin():
                review = (
                    session.query(TournamentCompletionReview)
                    .filter_by(review_token=token)
                    .one_or_none()
                )
                if review is None:
                    return {"status": "missing"}
                if review.status == "confirmed" and review.third_place_id:
                    candidate_index = next(
                        (
                            index
                            for index, candidate in enumerate(
                                json.loads(review.candidates)
                            )
                            if candidate["id"] == review.third_place_id
                        ),
                        -1,
                    )
                if review.status != "pending" and not review.third_place_id:
                    return {"status": "missing"}

                candidates = json.loads(review.candidates)
                if candidate_index not in range(len(candidates)):
                    raise ValueError("Invalid third-place selection.")
                selected = candidates[candidate_index]
                if review.status == "pending":
                    standings = json.loads(review.standings)
                    undefeated_ids = set(
                        json.loads(review.undefeated_player_ids)
                    )
                    self._write_standings(
                        session,
                        review.tournament_id,
                        standings,
                        review.participant_count,
                        undefeated_ids,
                        selected["id"],
                        candidates,
                    )
                    review.third_place_id = selected["id"]
                    review.confirmed_by = confirmer_id
                    review.status = "confirmed"

                final_standings = (
                    session.query(Standings)
                    .filter_by(tournament_id=review.tournament_id)
                    .order_by(Standings.position, Standings.player_name)
                    .all()
                )
                return {
                    "status": "confirmed",
                    "tournament_id": review.tournament_id,
                    "tournament_name": review.tournament_name,
                    "chat_id": review.chat_id,
                    "third_name": selected["name"],
                    "sent": review.result_sent,
                    "standings": [
                        {
                            "id": row.player_id,
                            "name": row.player_name,
                            "position": row.position,
                            "points": row.points,
                        }
                        for row in final_standings
                    ],
                    "candidates": candidates,
                    "third_place_id": review.third_place_id,
                    "review_token": review.review_token,
                    "participant_count": review.participant_count,
                }

    async def _send_final_results(self, result: dict[str, Any]) -> None:
        if result["sent"]:
            return
        fourth_place = next(
            candidate
            for candidate in result["candidates"]
            if candidate["id"] != result["third_place_id"]
        )
        lines = [
            f"🏆 Final results: {result['tournament_name']}",
            f"3rd: {result['third_name']}",
            f"4th: {fourth_place['name']}",
            "",
        ]
        for row in result["standings"]:
            position = (
                3
                if row["id"] == result["third_place_id"]
                else (
                    4
                    if row["id"] == fourth_place["id"]
                    else row["position"]
                )
            )
            lines.append(
                f"{position}. {row['name']} — {row['points']} league pts"
            )

        message = "\n".join(lines)
        chunks: list[str] = []
        current = ""
        for line in message.splitlines():
            if len(current) + len(line) + 1 > 3900:
                chunks.append(current.rstrip())
                current = ""
            current += line + "\n"
        if current.strip():
            chunks.append(current.rstrip())

        for chunk in chunks:
            await self.bot.send_message(chat_id=result["chat_id"], text=chunk)

        await asyncio.to_thread(
            self._mark_results_sent,
            result["tournament_id"],
        )

    def _mark_results_sent(self, tournament_id: str) -> None:
        with self.database_manager.get_session() as session:
            review = session.get(TournamentCompletionReview, tournament_id)
            if review is not None:
                review.result_sent = True
                session.commit()
