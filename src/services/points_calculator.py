"""Point calculation logic for Poyo TCG Players Championship."""

from typing import Any, Dict, Set

# Points for Monthly Tournaments
MONTHLY_POINTS = {
    1: 25,
    2: 18,
    3: 15,
    4: 12,
    5: 10,
    6: 8,
    7: 6,
    8: 4,
    9: 2,
    10: 1
}

# Points for Weekly Tournaments
WEEKLY_POINTS = {
    1: 6,
    2: 4,
    3: 3,
    4: 2,
    5: 1
}

def calculate_points(
    position: int,
    total_players: int,
    *,
    undefeated: bool = False,
) -> int:
    """
    Calculate points based on position and total tournament attendance.
    
    Args:
        position: The rank achieved (1-indexed)
        total_players: Number of players in the tournament. Tournaments with
            eight or more players use monthly scoring; smaller events use weekly.
        undefeated: Whether the player had no losses in non-bracket rounds.
            Undefeated players receive one additional point in monthly events.
        
    Returns:
        Points awarded for the position
    """
    if position < 1:
        raise ValueError("Position must be a positive, 1-indexed rank.")
    if total_players < 1:
        raise ValueError("A tournament must have at least one player.")

    is_monthly = total_players >= 8
    points_map = MONTHLY_POINTS if is_monthly else WEEKLY_POINTS
    points = points_map.get(position, 0)
    if is_monthly and undefeated:
        points += 1
    return points


def get_undefeated_player_ids(tournament: Dict[str, Any]) -> Set[str]:
    """Return players with no losses in completed non-bracket rounds."""
    swiss_rounds = tournament.get("swissNum")
    rounds = tournament.get("rounds")
    if not isinstance(swiss_rounds, int) or swiss_rounds < 1:
        return set()
    if not isinstance(rounds, list):
        return set()

    played: Set[str] = set()
    lost_or_unknown: Set[str] = set()
    for round_data in rounds:
        if not isinstance(round_data, dict):
            continue
        round_number = round_data.get("round")
        if not isinstance(round_number, int) or round_number > swiss_rounds:
            continue
        tables = round_data.get("tables")
        if not isinstance(tables, list):
            continue

        for table in tables:
            if not isinstance(table, dict):
                continue
            players = table.get("players")
            if not isinstance(players, list):
                continue
            player_ids = {
                player["id"]
                for player in players
                if isinstance(player, dict)
                and isinstance(player.get("id"), str)
                and player["id"].strip()
            }
            if not player_ids:
                continue
            played.update(player_ids)

            if str(table.get("status", "")).casefold() != "completed":
                lost_or_unknown.update(player_ids)
                continue

            winner_id = table.get("winner_id")
            if winner_id in {"Draw", "draw"}:
                continue
            if not isinstance(winner_id, str) or winner_id not in player_ids:
                lost_or_unknown.update(player_ids)
                continue
            lost_or_unknown.update(player_ids - {winner_id})

    return played - lost_or_unknown
