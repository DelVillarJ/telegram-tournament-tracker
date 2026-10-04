# Development Guide

This guide is for developers contributing to the Telegram Bot project.

## Getting Started

### Prerequisites

- Python 3.10+
- pip / virtualenv
- A Telegram account with @BotFather

### Setting Up Your Environment

```bash
# Clone the repository
git clone https://github.com/your-org/telegram-tournament-bot.git
cd telegram-tournament-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or: venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Setup development with debug mode
cp .env.template .env
# Edit .env and add your values
```

### Running the Bot

```bash
# Initialize database
python migrations/init.py

# Run migrations
python migrations/tournament_schema.py

# Start the bot
python src/main.py
```

## Project Structure

```
telegram-tournament-bot/
├── src/                    # Source code
│   ├── handlers/          # Bot command handlers
│   ├── models/            # Data models and schemas
│   ├── services/          # Business logic
│   └── utils/             # Utility functions
├── tests/                 # Test suites
├── config/               # Configuration files
├── docs/                 # Documentation
├── migrations/           # Database migrations
├── .github/workflows/    # CI/CD pipelines
├── requirements.txt      # Python dependencies
└── setup.py             # Package installer
```

## Development Workflow

### Adding New Commands

1. **Create handler function** in `src/handlers/__init__.py`:

```python
from aiogram import F, Router
from aiogram.filters.command import Command

@router.message(Command("example"))
async def example_command(message):
    await message.answer("This is an example command!")
```

2. **Test locally**: Add your bot token to `.env` and restart

3. **Run tests**: `pytest tests/test_handlers.py -v`

### Adding New Services

1. **Create service file** in `src/services/`:

```python
from typing import List, Dict
import requests

class MyService:
    def __init__(self):
        pass
    
    async def fetch_data(self) -> List[Dict]:
        # Implementation
        return []
```

2. **Add tests** in `tests/test_my_service.py`

3. **Update documentation** in `docs/`

### Writing Tests

Follow these patterns:

```python
import pytest
from unittest.mock import patch, MagicMock
from src.services.my_service import MyService


@pytest.fixture
def my_service():
    return MyService()


class TestMyService:
    def test_fetch_data_success(self, my_service):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [1, 2, 3]}
        
        with patch('requests.get', return_value=mock_response):
            result = my_service.fetch_data()
            
        assert len(result) == 3
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_handlers.py -v

# Run only async tests
pytest -m asyncio
```

## Code Style

We use the following tools:

- **Black** for code formatting
- **flake8** for style checking
- **mypy** for type checking
- **isort** for import sorting

Run before committing:

```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

## API Integration Guidelines

When integrating with TopDeck API:

1. **Handle errors gracefully**: Never expose API errors to users
2. **Rate limiting**: Respect API rate limits
3. **Retry logic**: Implement exponential backoff for transient errors
4. **Caching**: Cache responses appropriately
5. **Timeouts**: Set reasonable timeouts (default 30 seconds)

Example:

```python
async def fetch_with_retry(self, url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            return response.json()
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
```

## Database Migrations

When changing schema:

1. Add migration to `migrations/`
2. Write migration function
3. Test locally first
4. Run migrations before deploying

Example:

```python
# migrations/001_add_field.py
from sqlalchemy import Column, Integer

def upgrade():
    with db.engine.connect() as conn:
        metadata = sa.MetaData()
        with conn.begin():
            conn.execute(sa.text("""
                ALTER TABLE tournaments ADD COLUMN points_threshold INTEGER DEFAULT 0
            """))


def downgrade():
    with db.engine.connect() as conn:
        with conn.begin():
            conn.execute(sa.text("""
                ALTER TABLE tournaments DROP COLUMN points_threshold
            """))
```

## Debugging

### Enable debug logging

Set `DEBUG=true` in `.env`:

```bash
DEBUG=true
python src/main.py
```

### Common issues

**Connection refused**: Check bot token is valid and API is accessible

**Rate limited**: Wait or implement better rate limiting

**Database locked**: Close any other connections to SQLite

## CI/CD

Tests run automatically on:
- Push to main/develop branches
- Pull request reviews

The CI pipeline runs:
- Python tests with coverage
- Linting and formatting checks
- Security scans (Bandit, Safety)

To see CI results: [GitHub Actions link]

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes
4. Add tests
5. Run linting/tests locally
6. Commit with conventional commits
7. Push to branch
8. Open pull request

### Commit Messages

Use conventional commits:

```
feat: add new tournament tracking command
fix: resolve issue with standings update
docs: update user guide
test: add tests for notification service
refactor: simplify tournament handler logic
chore: update dependencies
```

## License

This project uses the MIT License. See LICENSE file for details.
