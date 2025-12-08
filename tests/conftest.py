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
def sample_data(fixtures_dir):
    """Load sample test data from JSON"""
    with open(fixtures_dir / "sample_data.json") as f:
        return json.load(f)


@pytest.fixture
def sample_hardware_packet(sample_data):
    """Sample hardware packet from ESP32"""
    return sample_data["sample_hardware_packet"]


@pytest.fixture
def sample_backend_packet(sample_data):
    """Sample backend API packet"""
    return sample_data["sample_backend_packet"]


@pytest.fixture
def sample_anchors(sample_data):
    """Sample anchor configurations"""
    return sample_data["sample_anchors"]


@pytest.fixture
def sample_products(sample_data):
    """Sample product catalog"""
    return sample_data["sample_products"]


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
