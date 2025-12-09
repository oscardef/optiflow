"""
Pytest configuration and shared fixtures for OptiFlow tests
"""

import pytest
import json
from pathlib import Path


@pytest.fixture(scope="session")
def fixtures_dir():
    """Return path to fixtures directory"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def hardware_formats(fixtures_dir):
    """Load hardware format test fixtures"""
    with open(fixtures_dir / "hardware_formats.json") as f:
        return json.load(f)


@pytest.fixture
def api_base_url():
    """Base URL for API integration tests"""
    return "http://localhost:8000"


# Markers for different test types
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (require running services)"
    )
    config.addinivalue_line(
        "markers", "hardware: Hardware tests (require physical devices)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests"
    )
