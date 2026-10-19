"""Tests for TopDeck's signed completion webhook workflow."""

import asyncio
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from src.models.database import (
    DefaultTournamentChannel,
    Standings,
    TopDeckWebhookEvent,
    TournamentChannel,
    TournamentCompletionReview,
)
from src.models.database_manager import DatabaseManager
from src.main import _run_polling_with_worker
from src.services.topdeck_webhook import (
    TopDeckWebhookService,
    verify_topdeck_signature,
)


def _signature(body: bytes, secret: str, timestamp: str = "1751500800000") -> str:
    digest = hmac.new(
        secret.encode(),
        timestamp.encode() + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def test_verify_topdeck_signature_uses_exact_raw_body():
    body = b'{"id":"evt_1"}'
    signature = _signature(body, "whsec_test")

    assert verify_topdeck_signature(body, signature, "whsec_test")
    assert not verify_topdeck_signature(body + b" ", signature, "whsec_test")
    assert not verify_topdeck_signature(body, signature, "wrong-secret")
    assert not verify_topdeck_signature(body, "invalid", "whsec_test")


@pytest.mark.asyncio
async def test_checkin_started_assigns_default_group_to_new_tournament(tmp_path):
    database_manager = DatabaseManager(f"sqlite:///{tmp_path / 'default-channel.db'}")
    await database_manager.create_all()
    with database_manager.get_session() as session:
        session.add(
            DefaultTournamentChannel(
                id="default",
                chat_id="-100123",
                assigned_by="42",
            )
        )
        session.commit()

    service = TopDeckWebhookService(
        database_manager,
        MagicMock(),
        MagicMock(),
        "whsec_test",
    )
    await service.process_event(
        {
            "id": "evt_checkin",
            "type": "tournament.checkin_started",
            "tid": "event-1",
            "data": {"stage": 1},
        }
    )
    await service.process_event(
        {
            "id": "evt_checkin_stage_2",
            "type": "tournament.checkin_started",
            "tid": "event-1",
            "data": {"stage": 2},
        }
    )

    with database_manager.get_session() as session:
        channel = session.get(TournamentChannel, "event-1")
        assert channel.chat_id == "-100123"
        assert channel.assigned_by == "42"
        assert session.query(TournamentChannel).count() == 1
    database_manager.close()


@pytest.mark.asyncio
async def test_checkin_started_does_not_overwrite_manual_destination(tmp_path):
    database_manager = DatabaseManager(f"sqlite:///{tmp_path / 'manual-channel.db'}")
    await database_manager.create_all()
    with database_manager.get_session() as session:
        session.add(
            DefaultTournamentChannel(
                id="default",
                chat_id="-100123",
                assigned_by="42",
            )
        )
        session.add(
            TournamentChannel(
                tournament_id="event-1",
                chat_id="-100456",
                assigned_by="84",
            )
        )
        session.commit()

    service = TopDeckWebhookService(
        database_manager,
        MagicMock(),
        MagicMock(),
        "whsec_test",
    )
    await service.process_event(
        {
            "id": "evt_checkin",
            "type": "tournament.checkin_started",
            "tid": "event-1",
            "data": {"stage": 1},
        }
    )

    with database_manager.get_session() as session:
        channel = session.get(TournamentChannel, "event-1")
        assert channel.chat_id == "-100456"
        assert channel.assigned_by == "84"
    database_manager.close()


@pytest.mark.asyncio
async def test_receiver_authenticates_and_deduplicates_event(tmp_path):
    database_manager = DatabaseManager(f"sqlite:///{tmp_path / 'webhooks.db'}")
    await database_manager.create_all()
    bot = MagicMock()
    api_client = MagicMock()
    service = TopDeckWebhookService(
        database_manager,
        bot,
        api_client,
        "whsec_test",
    )
    client = TestClient(TestServer(service.create_app()))
    await client.start_server()
    body = json.dumps(
        {
            "id": "evt_ping",
            "type": "ping",
            "created": 1751500800000,
            "tid": None,
            "tournament": None,
            "data": {},
        },
        separators=(",", ":"),
    ).encode()
    headers = {
        "X-TopDeck-Signature": _signature(body, "whsec_test"),
        "X-TopDeck-Event": "ping",
        "X-TopDeck-Event-Id": "evt_ping",
        "Content-Type": "application/json",
    }

    invalid = await client.post(
        "/webhooks/topdeck",
        data=body,
        headers={**headers, "X-TopDeck-Signature": "invalid"},
    )
    assert invalid.status == 401

    for _ in range(2):
        response = await client.post("/webhooks/topdeck", data=body, headers=headers)
        assert response.status == 200

    with database_manager.get_session() as session:
        assert session.query(TopDeckWebhookEvent).count() == 1
        assert session.get(TopDeckWebhookEvent, "evt_ping").status == "pending"

    await client.close()
    database_manager.close()


@pytest.mark.asyncio
async def test_weekly_event_imports_results_without_third_place_review(tmp_path):
    database_manager = DatabaseManager(f"sqlite:///{tmp_path / 'weekly.db'}")
    await database_manager.create_all()
    with database_manager.get_session() as session:
        session.add(
            TournamentChannel(
                tournament_id="weekly-1",
                chat_id="-100123",
                assigned_by="42",
            )
        )
        session.commit()

    bot = MagicMock()
    bot.send_message = AsyncMock()
    api_client = MagicMock()
    service = TopDeckWebhookService(
        database_manager,
        bot,
        api_client,
        "whsec_test",
    )
    event = {
        "id": "evt_weekly",
        "type": "tournament.finished",
        "created": 1751500800000,
        "tid": "weekly-1",
        "tournament": {"name": "Weekly Event"},
        "data": {
            "endedAt": 1751500800000,
            "participantCount": 4,
            "standings": [
                {"id": "alice", "name": "Alice", "standing": 1},
                {"id": "bob", "name": "Bob", "standing": 2},
                {"id": "carol", "name": "Carol", "standing": 3},
                {"id": "dave", "name": "Dave", "standing": 4},
            ],
        },
    }

    await service.process_event(event)

    api_client.search_tournaments.assert_not_called()
    bot.send_message.assert_awaited_once()
    assert "league standings updated" in bot.send_message.await_args.kwargs["text"]
    with database_manager.get_session() as session:
        assert session.get(TournamentCompletionReview, "weekly-1") is None
        rows = (
            session.query(Standings)
            .filter_by(tournament_id="weekly-1")
            .order_by(Standings.position)
            .all()
        )
        assert [(row.player_name, row.position, row.points) for row in rows] == [
            ("Alice", 1, 6),
            ("Bob", 2, 4),
            ("Carol", 3, 3),
            ("Dave", 4, 2),
        ]
    database_manager.close()


@pytest.mark.asyncio
async def test_weekly_event_uses_configured_default_destination(tmp_path):
    database_manager = DatabaseManager(f"sqlite:///{tmp_path / 'default-weekly.db'}")
    await database_manager.create_all()
    with database_manager.get_session() as session:
        session.add(
            TournamentChannel(
                tournament_id="weekly-default",
                chat_id="-1000000000000",
                assigned_by="42",
            )
        )
        session.commit()
    bot = MagicMock()
    bot.send_message = AsyncMock()
    service = TopDeckWebhookService(
        database_manager,
        bot,
        MagicMock(),
        "whsec_test",
        default_chat_id="-1004340474920",
    )

    await service.process_event(
        {
            "id": "evt_default_weekly",
            "type": "tournament.finished",
            "created": 1751500800000,
            "tid": "weekly-default",
            "tournament": {"name": "Weekly Event"},
            "data": {
                "endedAt": 1751500800000,
                "participantCount": 2,
                "standings": [
                    {"id": "alice", "name": "Alice", "standing": 1},
                    {"id": "bob", "name": "Bob", "standing": 2},
                ],
            },
        }
    )

    assert bot.send_message.await_args.kwargs["chat_id"] == "-1004340474920"
    with database_manager.get_session() as session:
        channel = session.get(TournamentChannel, "weekly-default")
        assert channel.chat_id == "-1004340474920"
        assert channel.assigned_by == "configuration"
        assert session.query(Standings).filter_by(
            tournament_id="weekly-default"
        ).count() == 2
    database_manager.close()


@pytest.mark.asyncio
async def test_monthly_event_uses_configured_default_destination(tmp_path):
    database_manager = DatabaseManager(f"sqlite:///{tmp_path / 'default-monthly.db'}")
    await database_manager.create_all()
    bot = MagicMock()
    bot.send_message = AsyncMock()
    api_client = MagicMock()
    api_client.search_tournaments.return_value = [
        {
            "TID": "monthly-default",
            "rounds": [
                {
                    "round": "Top 4",
                    "tables": [
                        {
                            "players": [
                                {"id": "alice", "name": "Alice"},
                                {"id": "bob", "name": "Bob"},
                            ],
                            "winner_id": "alice",
                        },
                        {
                            "players": [
                                {"id": "carol", "name": "Carol"},
                                {"id": "dave", "name": "Dave"},
                            ],
                            "winner_id": "carol",
                        },
                    ],
                }
            ],
        }
    ]
    service = TopDeckWebhookService(
        database_manager,
        bot,
        api_client,
        "whsec_test",
        default_chat_id="-1004340474920",
    )

    await service.process_event(
        {
            "id": "evt_default_monthly",
            "type": "tournament.finished",
            "created": 1751500800000,
            "tid": "monthly-default",
            "tournament": {"name": "Monthly Event"},
            "data": {
                "endedAt": 1751500800000,
                "participantCount": 8,
                "standings": [
                    {"id": "alice", "name": "Alice", "standing": 1},
                    {"id": "bob", "name": "Bob", "standing": 2},
                    {"id": "carol", "name": "Carol", "standing": 3},
                    {"id": "dave", "name": "Dave", "standing": 4},
                ],
            },
        }
    )

    assert bot.send_message.await_args.kwargs["chat_id"] == "-1004340474920"
    with database_manager.get_session() as session:
        channel = session.get(TournamentChannel, "monthly-default")
        assert channel.chat_id == "-1004340474920"
        review = session.get(TournamentCompletionReview, "monthly-default")
        assert review.chat_id == "-1004340474920"
        assert review.status == "pending"
    database_manager.close()


@pytest.mark.asyncio
async def test_polling_shutdown_cancels_webhook_worker():
    dispatcher = MagicMock()
    dispatcher.start_polling = AsyncMock()
    stopped = asyncio.Event()

    class Worker:
        async def run_worker(self):
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()

    await _run_polling_with_worker(dispatcher, MagicMock(), Worker())
    assert stopped.is_set()


@pytest.mark.asyncio
async def test_unexpected_webhook_worker_exit_stops_polling():
    stopped = asyncio.Event()

    class Dispatcher:
        async def start_polling(self, _bot):
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()

    class Worker:
        async def run_worker(self):
            raise ValueError("database unavailable")

    with pytest.raises(ValueError, match="database unavailable"):
        await _run_polling_with_worker(Dispatcher(), MagicMock(), Worker())
    assert stopped.is_set()


@pytest.mark.asyncio
async def test_finished_event_prompts_for_third_and_saves_confirmed_results(tmp_path):
    database_manager = DatabaseManager(f"sqlite:///{tmp_path / 'finished.db'}")
    await database_manager.create_all()
    with database_manager.get_session() as session:
        session.add(
            TournamentChannel(
                tournament_id="event-1",
                chat_id="-100123",
                assigned_by="42",
            )
        )
        session.commit()

    bot = MagicMock()
    bot.send_message = AsyncMock()
    api_client = MagicMock()
    api_client.search_tournaments.return_value = [
        {
            "TID": "event-1",
            "swissNum": 1,
            "rounds": [
                {
                    "round": 1,
                    "tables": [
                        {
                            "players": [
                                {"id": "alice", "name": "Alice"},
                                {"id": "bob", "name": "Bob"},
                            ],
                            "status": "completed",
                            "winner_id": "alice",
                        }
                    ],
                },
                {
                    "round": "Top 4",
                    "roundLabel": "Top 4",
                    "tables": [
                        {
                            "players": [
                                {"id": "alice", "name": "Alice"},
                                {"id": "carol", "name": "Carol"},
                            ],
                            "winner_id": "alice",
                        },
                        {
                            "players": [
                                {"id": "bob", "name": "Bob"},
                                {"id": "dave", "name": "Dave"},
                            ],
                            "winner_id": "bob",
                        },
                    ],
                },
            ],
        }
    ]
    service = TopDeckWebhookService(
        database_manager,
        bot,
        api_client,
        "whsec_test",
    )
    event = {
        "id": "evt_finished",
        "type": "tournament.finished",
        "created": 1751500800000,
        "tid": "event-1",
        "tournament": {"name": "Championship"},
        "data": {
            "endedAt": 1751500800000,
            "participantCount": 8,
            "standings": [
                {"id": "alice", "name": "Alice", "standing": 1, "wins": 4},
                {"id": "bob", "name": "Bob", "standing": 2, "wins": 3},
                {"id": "carol", "name": "Carol", "standing": 3, "wins": 2},
                {"id": "dave", "name": "Dave", "standing": 3, "wins": 2},
            ],
        },
    }

    await service.process_event(event)

    prompt = bot.send_message.await_args.kwargs
    assert prompt["chat_id"] == "-100123"
    assert "third-place" in prompt["text"].lower()
    token = prompt["reply_markup"].inline_keyboard[0][0].callback_data.split(":")[1]

    response = await service.confirm_third_place(token, 0, "42")
    assert response == "Third place confirmed as Carol."
    assert bot.send_message.await_count == 2
    final_message = bot.send_message.await_args.kwargs["text"]
    assert "3rd: Carol" in final_message
    assert "4th: Dave" in final_message

    with database_manager.get_session() as session:
        review = session.get(TournamentCompletionReview, "event-1")
        rows = (
            session.query(Standings)
            .filter_by(tournament_id="event-1")
            .order_by(Standings.position)
            .all()
        )
        assert review.status == "confirmed"
        assert review.result_sent
        assert [(row.player_name, row.position) for row in rows] == [
            ("Alice", 1),
            ("Bob", 2),
            ("Carol", 3),
            ("Dave", 4),
        ]
        assert rows[0].points == 26
        assert rows[2].points == 15
        assert rows[3].points == 12

    database_manager.close()
