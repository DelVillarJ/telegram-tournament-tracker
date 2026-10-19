"""Tests for TopDeck.gg's Tournaments V2 client."""

from unittest.mock import Mock, patch

import pytest
import requests

from src.topdeck._api import TopDeckAPI


@pytest.mark.parametrize(
    ("base_url", "expected_url"),
    [
        ("https://topdeck.gg", "https://topdeck.gg/api/v2/tournaments"),
        ("https://topdeck.gg/api/", "https://topdeck.gg/api/v2/tournaments"),
    ],
)
def test_query_mode_uses_documented_endpoint_and_fields(base_url, expected_url):
    client = TopDeckAPI("test-api-key", base_url)
    response = Mock()
    response.json.return_value = [{"TID": "event-1", "tournamentName": "Event"}]

    with patch("src.topdeck._api.requests.post", return_value=response) as post:
        result = client.search_tournaments(
            game="One Piece",
            format="",
            start=0,
            participant_min=0,
            columns=["name", "wins"],
            rounds=True,
            tables=["table", "winner"],
            players=["name", "decklist"],
        )

    assert result == [{"TID": "event-1", "tournamentName": "Event"}]
    post.assert_called_once_with(
        expected_url,
        json={
            "game": "One Piece",
            "format": "",
            "start": 0,
            "participantMin": 0,
            "columns": ["name", "wins"],
            "rounds": True,
            "tables": ["table", "winner"],
            "players": ["name", "decklist"],
        },
        headers={
            "Authorization": "test-api-key",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    response.raise_for_status.assert_called_once_with()


def test_tid_mode_omits_query_filters():
    client = TopDeckAPI("test-api-key")
    response = Mock()
    response.json.return_value = []

    with patch("src.topdeck._api.requests.post", return_value=response) as post:
        assert client.search_tournaments(
            tid=["event-1", "event-2"],
            game="Magic: The Gathering",
            format="Modern",
            last=30,
            participant_min=8,
        ) == []

    assert post.call_args.kwargs["json"] == {"TID": ["event-1", "event-2"]}


@pytest.mark.parametrize(
    ("base_url", "expected_url"),
    [
        (
            "https://topdeck.gg",
            "https://topdeck.gg/api/v2/me/tournaments?filter=all",
        ),
        (
            "https://topdeck.gg/api/",
            "https://topdeck.gg/api/v2/me/tournaments?filter=all",
        ),
    ],
)
def test_get_my_tournaments_uses_authenticated_account_endpoint(base_url, expected_url):
    client = TopDeckAPI("test-api-key", base_url)
    response = Mock()
    response.json.return_value = [{"TID": "event-1", "tournamentName": "Event"}]

    with patch("src.topdeck._api.requests.get", return_value=response) as get:
        result = client.get_my_tournaments()

    assert result == [{"TID": "event-1", "tournamentName": "Event"}]
    get.assert_called_once_with(
        expected_url,
        headers={
            "Authorization": "test-api-key",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    response.raise_for_status.assert_called_once_with()


def test_get_my_tournaments_rejects_unexpected_response_shape():
    client = TopDeckAPI("test-api-key")
    response = Mock()
    response.json.return_value = {"tournaments": []}

    with patch("src.topdeck._api.requests.get", return_value=response):
        with pytest.raises(ValueError, match="unexpected response"):
            client.get_my_tournaments()


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"game": "Magic: The Gathering"},
        {"format": "Modern"},
        {"game": "Magic: The Gathering", "format": "Modern", "last": 7, "start": 1},
        {"tid": ""},
        {"tid": []},
    ],
)
def test_invalid_search_parameters_raise_value_error(kwargs):
    client = TopDeckAPI("test-api-key")

    with pytest.raises(ValueError):
        client.search_tournaments(**kwargs)


def test_http_errors_are_raised():
    client = TopDeckAPI("test-api-key")
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("Unauthorized")

    with patch("src.topdeck._api.requests.post", return_value=response):
        with pytest.raises(requests.HTTPError, match="Unauthorized"):
            client.search_tournaments(tid="event-1")


def test_unexpected_response_shape_is_rejected():
    client = TopDeckAPI("test-api-key")
    response = Mock()
    response.json.return_value = {"tournaments": []}

    with patch("src.topdeck._api.requests.post", return_value=response):
        with pytest.raises(ValueError, match="unexpected response"):
            client.search_tournaments(tid="event-1")
