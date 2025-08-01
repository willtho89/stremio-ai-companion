# Stremio AI Companion Tests

This directory contains tests for the Stremio AI Companion application. The tests are organized into unit tests and integration tests.

## Test Structure

- `tests/unit/`: Unit tests for individual components
  - `api/`: Tests for API endpoints
  - `core/`: Tests for core modules
  - `models/`: Tests for data models
  - `services/`: Tests for service modules
  - `utils/`: Tests for utility functions
- `tests/integration/`: Integration tests for key workflows
- `conftest.py`: Shared fixtures and configuration for tests

## Running Tests

### Prerequisites

- Python 3.9 or higher
- All dependencies installed

You can install all required dependencies (including test dependencies) with:

```bash
pip install -r requirements-dev.txt
```

This will install both the application dependencies and the test dependencies (`pytest`, `pytest-asyncio`, `pytest-cov`, `httpx`).

### Running All Tests

To run all tests:

```bash
pytest
```

### Running Specific Test Types

To run only unit tests:

```bash
pytest tests/unit/
```

To run only integration tests:

```bash
pytest tests/integration/
```

To run tests with a specific marker:

```bash
pytest -m unit
pytest -m integration
pytest -m api
```

### Running Specific Test Files

To run tests in a specific file:

```bash
pytest tests/unit/utils/test_parsing.py
```

### Running Specific Test Functions

To run a specific test function:

```bash
pytest tests/unit/utils/test_parsing.py::TestParseQueryWithYear::test_with_year
```

## Test Coverage

To generate a test coverage report:

```bash
pip install pytest-cov
pytest --cov=app
```

For a more detailed HTML report:

```bash
pytest --cov=app --cov-report=html
```

This will create a `htmlcov` directory with an HTML report that you can open in your browser.

## Writing Tests

### Unit Tests

Unit tests should test individual components in isolation. Use mocking to avoid dependencies on external services.

Example:

```python
import pytest
from unittest.mock import patch, MagicMock
from app.utils.parsing import parse_movie_with_year

def test_parse_movie_with_year():
    title, year = parse_movie_with_year("The Matrix (1999)")
    assert title == "The Matrix"
    assert year == 1999
```

### Integration Tests

Integration tests should test the interaction between multiple components. They may still use mocking for external services.

Example:

```python
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.api import app

@pytest.mark.integration
def test_movie_suggestions_workflow(client):
    # Test the end-to-end workflow
    with patch('app.services.llm.LLMService.generate_movie_suggestions') as mock:
        mock.return_value = ["The Matrix (1999)"]
        response = client.get("/config/encrypted_config/catalog/movie/ai_companion_movie.json?search=sci-fi")
        assert response.status_code == 200
        assert "metas" in response.json()
```

## Python Path Configuration

The tests need to import modules from the main application package (`app`). To make this work, the `conftest.py` file adds the project root directory to the Python path:

```python
import os
import sys

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
```

This allows tests to import modules from the `app` package without needing to install the package in development mode. If you're getting import errors when running tests, make sure this code is present in the `conftest.py` file.

## Test Fixtures

Common test fixtures are defined in `conftest.py`. These include:

- `sample_config`: A sample Config object
- `sample_config_with_posterdb`: A sample Config object with RPDB enabled
- `sample_movie_suggestions`: A sample MovieSuggestions object
- `sample_tmdb_movie`: Sample TMDB movie data
- `sample_stremio_meta`: A sample StremioMeta object

You can use these fixtures in your tests by adding them as parameters to your test functions:

```python
def test_function(sample_config):
    # Use sample_config in your test
    assert sample_config.model_name == "openrouter/horizon-alpha:online"
```