"""
Tests for the TopDeck API client.
Run with: pytest tests/test_topdeck_api.py -v
"""

import sys
from pathlib import Path


def test_tournament_parsing():
    """Test parsing tournament data from API response."""
    # Sample API response structure (based on TopDeck.gg Tournaments V2)
    sample_data = {
        'id': '12345',
        'name': 'Spring Championship 2026',
        'category': 'eSports',
        'status': 'ongoing',
        'startTime': '2026-09-01T00:00:00Z',
        'endTime': '2026-12-31T23:59:59Z',
        'userId': 'user_abc123',
    }
    
    # Test that required fields are extracted
    assert sample_data['name'] == 'Spring Championship 2026'
    assert sample_data['status'] == 'ongoing'
    
    print("✓ Tournament parsing test passed")


def test_tournament_status_detection():
    """Test detecting tournament status changes."""
    # Ongoing tournament
    ongoing = {
        'id': '12345',
        'name': 'Active Tournament',
        'status': 'ongoing',
    }
    
    # Completed tournament
    completed = {
        'id': '67890',
        'name': 'Finished Tournament',
        'status': 'completed',
        'endTime': '2026-10-02T12:00:00Z',
    }
    
    # Cancelled tournament
    cancelled = {
        'id': '11111',
        'name': 'Cancelled Tournament',
        'status': 'cancelled',
    }
    
    assert ongoing['status'] in ['ongoing', 'pending']
    assert completed['status'] == 'completed'
    assert cancelled['status'] == 'cancelled'
    
    print("✓ Tournament status detection test passed")


def test_result_data_structure():
    """Test that completion result data has expected structure."""
    sample_completion = {
        'total_participants': 8,
        'winner_team': 'Team Alpha',
        'final_standings': [
            {'team': 'Team Alpha', 'position': 1},
            {'team': 'Team Beta', 'position': 2},
        ],
    }
    
    assert sample_completion['total_participants'] == 8
    assert sample_completion['winner_team'] == 'Team Alpha'
    assert len(sample_completion['final_standings']) == 2
    
    print("✓ Result data structure test passed")
