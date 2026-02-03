# Testing Guide

This document describes the testing setup and how to run tests for the UWB Localization System.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_core.py             # Core localization tests
├── test_input_adapters.py   # Input adapter tests
├── test_output_adapters.py  # Output adapter tests
└── test_integration.py      # Integration tests
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_core.py

# Run specific test class
pytest tests/test_core.py::TestLocalizationEngine

# Run specific test function
pytest tests/test_core.py::TestLocalizationEngine::test_engine_initialization
```

### With Coverage

```bash
# Install test dependencies first
pip install -r requirements-dev.txt

# Run with coverage
pytest --cov=uwb_localizer --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Using Makefile

```bash
make test        # Run all tests with coverage
make test-fast   # Run tests, stop on first failure
make lint        # Run linters
make format      # Format code
```

## Test Categories

### Unit Tests

- **test_core.py**: Tests for core localization algorithms
  - Calibration functions (linear, quadratic, cubic)
  - Trilateration algorithm
  - Multilateration algorithm
  - LocalizationEngine class

- **test_input_adapters.py**: Tests for input adapters
  - Serial adapter
  - UDP adapter
  - File adapter
  - MQTT adapter (requires paho-mqtt)

- **test_output_adapters.py**: Tests for output adapters
  - Console adapter
  - UDP adapter
  - File adapter
  - MAVLink adapter (requires pymavlink)
  - MAVROS adapter (requires rclpy)
  - Multi-output adapter

### Integration Tests

- **test_integration.py**: End-to-end tests
  - File input to file output
  - Calibration pipeline
  - Range filtering

## Test Fixtures

Shared fixtures are defined in `tests/conftest.py`:

- `standard_anchors`: Standard anchor positions for testing
- `standard_engine`: Pre-configured LocalizationEngine
- `test_distances`: Test distance measurements
- `temp_file`: Temporary file path

## Writing New Tests

### Example Unit Test

```python
def test_my_function():
    """Test description."""
    result = my_function(input_value)
    assert result == expected_value
```

### Example Test with Fixture

```python
def test_engine_calculation(standard_engine, test_distances):
    """Test position calculation."""
    position = standard_engine.calculate_position(test_distances)
    assert position is not None
    x, y, z = position
    assert abs(x - 1.0) < 0.1
```

### Example Mock Test

```python
from unittest.mock import Mock, patch

@patch('module.ExternalDependency')
def test_with_mock(mock_dependency):
    """Test with mocked dependency."""
    mock_dependency.return_value = expected_value
    result = function_using_dependency()
    assert result == expected_value
```

## Continuous Integration

Tests are automatically run on:
- Push to `main` or `develop` branches
- Pull requests
- Multiple Python versions (3.8-3.12)

See `.github/workflows/ci.yml` for CI configuration.

## Coverage Goals

- Aim for >80% code coverage
- Focus on testing core functionality
- Mock external dependencies (serial ports, network, etc.)

## Troubleshooting

### Tests Fail Due to Missing Dependencies

Some tests require optional dependencies:
- `paho-mqtt` for MQTT adapter tests
- `rclpy` for MAVROS adapter tests
- `pymavlink` for MAVLink adapter tests

Install these if you want to run all tests:
```bash
pip install paho-mqtt pymavlink
# rclpy requires ROS2 installation
```

### Tests Requiring Hardware

Some tests may require hardware (e.g., serial ports). These are marked with `@pytest.mark.requires_hardware` and can be skipped:

```bash
pytest -m "not requires_hardware"
```
