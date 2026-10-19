"""Tests for Poyo League point calculations."""

import pytest

from src.services.points_calculator import (
    calculate_points,
    get_undefeated_player_ids,
)


@pytest.mark.parametrize(
    ("position", "total_players", "expected"),
    [
        (1, 8, 25),
        (2, 8, 18),
        (3, 8, 15),
        (4, 8, 12),
        (5, 8, 10),
        (6, 8, 8),
        (7, 8, 6),
        (8, 8, 4),
        (9, 8, 2),
        (10, 8, 1),
        (11, 8, 0),
    ],
)
def test_monthly_tournament_points(position, total_players, expected):
    assert calculate_points(position, total_players) == expected


@pytest.mark.parametrize(
    ("position", "total_players", "expected"),
    [
        (1, 7, 6),
        (2, 7, 4),
        (3, 7, 3),
        (4, 7, 2),
        (5, 7, 1),
        (6, 7, 0),
        (1, 1, 6),
        (1, 8, 25),
    ],
)
def test_tournament_points_use_player_count(position, total_players, expected):
    assert calculate_points(position, total_players) == expected


@pytest.mark.parametrize(
    ("position", "total_players"),
    [(0, 8), (1, 0)],
)
def test_invalid_position_or_player_count_raises(position, total_players):
    with pytest.raises(ValueError):
        calculate_points(position, total_players)


@pytest.mark.parametrize(
    ("position", "total_players", "undefeated", "expected"),
    [
        (1, 8, True, 26),
        (10, 8, True, 2),
        (11, 8, True, 1),
        (1, 8, False, 25),
        (1, 7, True, 6),
    ],
)
def test_undefeated_bonus_applies_only_to_monthly_events(
    position, total_players, undefeated, expected
):
    assert calculate_points(
        position,
        total_players,
        undefeated=undefeated,
    ) == expected


def test_undefeated_players_include_draws_but_exclude_losses_and_bracket():
    tournament = {
        "swissNum": 2,
        "rounds": [
            {
                "round": 1,
                "tables": [
                    {
                        "players": [{"id": "winner"}, {"id": "loser"}],
                        "winner_id": "winner",
                        "status": "Completed",
                    },
                    {
                        "players": [{"id": "draw-a"}, {"id": "draw-b"}],
                        "winner_id": "Draw",
                        "status": "Completed",
                    },
                ],
            },
            {
                "round": 2,
                "tables": [
                    {
                        "players": [{"id": "winner"}, {"id": "draw-a"}],
                        "winner_id": "winner",
                        "status": "Completed",
                    },
                    {
                        "players": [{"id": "draw-b"}, {"id": "loser"}],
                        "winner_id": "draw-b",
                        "status": "Completed",
                    },
                ],
            },
            {
                "round": 3,
                "tables": [
                    {
                        "players": [{"id": "winner"}, {"id": "draw-b"}],
                        "winner_id": "draw-b",
                        "status": "Completed",
                    }
                ],
            },
        ],
    }

    assert get_undefeated_player_ids(tournament) == {"winner", "draw-b"}


def test_undefeated_players_require_round_history():
    assert get_undefeated_player_ids({"swissNum": 0, "rounds": []}) == set()
    assert get_undefeated_player_ids({"swissNum": 3}) == set()
