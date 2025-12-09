# OptiFlow Test Suite

Comprehensive test suite for the OptiFlow inventory tracking system.

## Structure

```
tests/
├── conftest.py              # Pytest configuration and shared fixtures
├── __init__.py
│
├── unit/                    # Unit tests (fast, no dependencies)
│   ├── __init__.py
│   ├── test_triangulation.py    # Position calculation logic
│   └── test_schemas.py          # Pydantic schema validation
│
├── integration/             # Integration tests (require services)
│   ├── __init__.py
│   ├── test_system.py           # End-to-end system flow
│   └── test_mqtt_hardware.py   # MQTT hardware validation
│
└── fixtures/                # Test data and fixtures
    └── sample_data.json         # Sample packets and configurations
```

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-cov requests paho-mqtt

# For integration tests: Start Docker services
docker compose up -d
```

### Run All Tests

```bash
# Quick run - all tests with simple runner
python tests/run_tests.py

# Or use pytest directly
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=backend/app --cov-report=html
```

### Run Specific Test Types

```bash
# Unit tests only (fast) - using runner
python tests/run_tests.py --unit

# Integration tests only (requires services) - using runner
python tests/run_tests.py --integration

# Or use pytest directly
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest -m unit
pytest -m integration

# Run specific test file
pytest tests/unit/test_triangulation.py -v

# Run specific test function
pytest tests/unit/test_triangulation.py::TestTriangulationService::test_calculate_with_two_measurements -v
```

### Test Runner Options

The `run_tests.py` script provides convenient shortcuts:

```bash
python tests/run_tests.py              # All tests, verbose
python tests/run_tests.py --unit       # Unit tests only
python tests/run_tests.py --integration # Integration tests only
python tests/run_tests.py --coverage   # With coverage report
python tests/run_tests.py --html-report # Generate HTML coverage
python tests/run_tests.py --failed     # Re-run failed tests
python tests/run_tests.py -k triangulation # Filter by keyword
python tests/run_tests.py --help       # See all options
```

### Run Tests by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only hardware tests
pytest -m hardware

# Exclude slow tests
pytest -m "not slow"
```

## Test Types

### Unit Tests

**Purpose:** Test individual components in isolation  
**Speed:** Fast (< 1s per test)  
**Dependencies:** None (pure Python)  
**Location:** `tests/unit/`

**Examples:**
- `test_triangulation.py` - Position calculation algorithms
- `test_schemas.py` - Data validation and serialization

### Integration Tests

**Purpose:** Test component interactions and full data flow  
**Speed:** Slower (1-10s per test)  
**Dependencies:** Docker services (backend, databases)  
**Location:** `tests/integration/`

**Examples:**
- `test_system.py` - Complete data flow from API to database
- `test_mqtt_hardware.py` - MQTT broker and hardware communication

### Hardware Tests

**Purpose:** Validate production hardware communication  
**Speed:** Variable  
**Dependencies:** Physical ESP32 devices, MQTT broker  
**Location:** `tests/integration/test_mqtt_hardware.py`

**Usage:**
```bash
# Listen for hardware data
python tests/integration/test_mqtt_hardware.py --broker 172.20.10.4

# Send START signal and listen
python tests/integration/test_mqtt_hardware.py --start
```

## Writing Tests

### Unit Test Example

```python
import pytest
from app.triangulation import TriangulationService

class TestMyComponent:
    def setup_method(self):
        """Setup before each test"""
        self.service = TriangulationService()
    
    def test_basic_functionality(self):
        """Test description"""
        result = self.service.calculate_position([], [], "test")
        assert result is None
```

### Integration Test Example

```python
import pytest
import requests

@pytest.mark.integration
def test_api_endpoint(api_base_url):
    """Test API endpoint"""
    response = requests.get(f"{api_base_url}/data/items")
    assert response.status_code == 200
```

## Test Fixtures

Shared test data is available via fixtures defined in `conftest.py`:

```python
def test_with_fixtures(sample_anchors, sample_products):
    """Use predefined test data"""
    assert len(sample_anchors) == 4
    assert len(sample_products) == 3
```

## Continuous Integration

For CI/CD pipelines:

```bash
# Run tests with JUnit XML output
pytest --junitxml=test-results.xml

# Run with coverage
pytest --cov=backend/app --cov-report=xml --cov-report=term

# Run only fast tests
pytest -m "unit and not slow"
```

## Troubleshooting

### Integration Tests Failing

**Problem:** `Backend not available` errors

**Solution:**
```bash
# Check services are running
docker compose ps

# Start services
docker compose up -d

# Check backend health
curl http://localhost:8000/docs
```

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'app'`

**Solution:**
```bash
# Run from project root
cd /path/to/optiflow
pytest

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
```

### Hardware Tests Not Receiving Data

**Problem:** No messages from ESP32

**Solution:**
```bash
# Send START signal to ESP32
mosquitto_pub -h 172.20.10.4 -t store/control -m 'START'

# Check MQTT broker
mosquitto_sub -h 172.20.10.4 -t "store/#" -v
```

## Coverage Reports

Generate HTML coverage reports:

```bash
pytest --cov=backend/app --cov-report=html
open htmlcov/index.html  # View in browser
```

## Best Practices

1. **Keep unit tests fast** - No network calls, no database access
2. **Use fixtures** - Share common test data via `conftest.py`
3. **Mark tests** - Use `@pytest.mark.integration` for tests requiring services
4. **Clean up** - Integration tests should clean up test data
5. **Descriptive names** - Test names should describe what they test
6. **One assertion concept** - Each test should verify one behavior

## Related Documentation

- [Backend API Reference](../backend/README.md)
- [Hardware Integration Guide](../firmware/FIRMWARE_ARCHITECTURE.md)
- [System Architecture](../README.md#architecture)
