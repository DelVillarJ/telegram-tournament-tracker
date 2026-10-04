"""Pytest configuration."""

import sys
from pathlib import Path

# Auto-discover pytest plugins
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


def pytest_collection_modifyitems(session, config, items):
    """Automatically add asyncio marker to all tests."""
    for item in items:
        if "async" not in item.keywords and "pytest_asyncio" in str(item.get_closest_marker("asyncio")):
            item.add_marker(pytest.mark.asyncio())


# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
