"""
Input validation helpers for the Telegram bot.
Provides utility functions for validating user inputs and data structures.
"""


def validate_tournament_id(tournament_id: str) -> bool:
    """
    Validate that a tournament ID is in correct format.
    
    Args:
        tournament_id: Tournament ID string to validate.
    
    Returns:
        True if valid, False otherwise.
    """
    if not tournament_id or not isinstance(tournament_id, str):
        return False
    
    # Tournament IDs from TopDeck API are typically numeric or alphanumeric
    try:
        int(tournament_id)
        return len(tournament_id) > 0
    except ValueError:
        # Allow alphanumeric IDs as well
        return len(tournament_id) > 0 and not tournament_id.startswith('/')


def validate_user_id(user_id: str) -> bool:
    """
    Validate that a user ID is in correct format.
    
    Args:
        user_id: User ID string to validate.
    
    Returns:
        True if valid, False otherwise.
    """
    if not user_id or not isinstance(user_id, str):
        return False
    
    # User IDs from TopDeck can be numeric strings
    try:
        int(user_id)
        return len(user_id) > 0 and len(user_id) <= 20  # Reasonable length
    except ValueError:
        return False


def validate_command_arguments(
    command_name: str,
    arguments: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Validate command arguments.
    
    Args:
        command_name: Name of the command being executed.
        arguments: Command arguments (optional).
    
    Returns:
        Tuple of (is_valid, error_message).
    """
    if not arguments or not arguments.strip():
        return False, "Missing required argument for this command."
    
    # Basic validation based on command type
    if 'tournament' in command_name.lower():
        if not validate_tournament_id(arguments):
            return False, f"Invalid tournament ID format: {arguments}"
    
    return True, ""


def normalize_tournament_data(tournament: Dict) -> Dict[str, Any]:
    """
    Normalize tournament data from various sources.
    
    Args:
        tournament: Raw tournament data from API or database.
    
    Returns:
        Normalized tournament dictionary with consistent field names.
    """
    if not isinstance(tournament, dict):
        return {}
    
    normalized = {
        'id': str(tournament.get('topdeck_tournament_id', '')),
        'name': str(tournament.get('name', '')),
        'category': str(tournament.get('category', '')),
        'status': str(tournament.get('status', 'pending')),
    }
    
    # Standardize date fields
    date_fields = ['start_date', 'end_date', 'registration_deadline']
    for field in date_fields:
        value = tournament.get(field)
        if value and hasattr(value, 'strftime'):
            normalized[field] = value.strftime('%Y-%m-%dT%H:%M:%S')
        elif isinstance(value, str):
            normalized[field] = value.strip()
    
    # Handle optional numeric fields
    numeric_fields = ['total_prize_pool']
    for field in numeric_fields:
        value = tournament.get(field)
        if value is not None and value != '':
            try:
                normalized[field] = float(value)
            except (ValueError, TypeError):
                pass
    
    return normalized


def parse_standings_data(standings: List[Dict]) -> List[Dict[str, Any]]:
    """
    Parse and normalize standings data.
    
    Args:
        standings: List of standings dictionaries from API or database.
    
    Returns:
        Sorted list of standings by position.
    """
    if not isinstance(standings, list):
        return []
    
    parsed = []
    for standing in standings:
        if isinstance(standing, dict):
            parsed.append({
                'position': int(standing.get('position', len(parsed) + 1)),
                'team_name': str(standing.get('team_name', '')),
                'points': int(float(standing.get('points', 0))) if standing.get('points') is not None else 0,
                'games_played': int(standing.get('games_played', 0)),
                'wins': int(standing.get('wins', 0)),
                'losses': int(standing.get('losses', 0)),
                'draws': int(standing.get('draws', 0)),
            })
    
    # Sort by position
    parsed.sort(key=lambda x: x['position'])
    
    return parsed


def validate_tournament_rules(tournament: Dict) -> bool:
    """
    Validate that tournament data meets required fields.
    
    Args:
        tournament: Tournament data to validate.
    
    Returns:
        True if valid, False otherwise.
    """
    required_fields = ['name', 'status']
    
    for field in required_fields:
        if field not in tournament or not tournament[field]:
            return False
    
    return True
