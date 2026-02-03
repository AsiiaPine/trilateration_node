# Universal UWB Localization System

A flexible, modular system for parsing UWB distance measurements, calculating position using multilateration, and outputting to various protocols (MAVLink, MAVROS, UDP, file, console).

## Features

- **Flexible Input**: Support for serial, MQTT, UDP, and file inputs
- **Flexible Output**: Support for MAVLink, MAVROS, UDP, file, and console outputs
- **Modular Architecture**: Easy to extend with new input/output adapters
- **Configuration-Based**: Simple TOML configuration file
- **Robust Algorithm**: Uses proven multilateration algorithm from RTK-DW1000 project

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. For optional adapters:
- **MQTT**: `pip install paho-mqtt`
- **MAVROS/ROS2**: Install ROS2 and `rclpy` (system-dependent)

## Testing

### Quick Start

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=uwb_localizer --cov-report=html

# Or use Makefile
make test        # Run all tests with coverage
make test-fast   # Run tests, stop on first failure
make lint        # Run linters
make format      # Format code with black
```

See [TESTING.md](TESTING.md) for detailed testing documentation.

## Configuration

Edit `config.toml` to configure:

### Anchor Positions
Define anchor positions in the `[localization]` section:
```toml
[localization]
anchor_positions = {
    1 = [0.0, 0.0, 0.0],
    2 = [3.0, 0.0, 0.0],
    3 = [0.0, 3.0, 0.0]
}
```

### Input Adapter
Choose input source in `[input]` section:
- **Serial**: `type = "serial"` (default)
- **MQTT**: `type = "mqtt"`
- **UDP**: `type = "udp"`
- **File**: `type = "file"`

### Output Adapter
Choose output destination in `[output]` section:
- **Console**: `type = "console"` (default)
- **MAVLink**: `type = "mavlink"`
- **MAVROS**: `type = "mavros"`
- **UDP**: `type = "udp"`
- **File**: `type = "file"`
- **Multiple**: `type = "console,mavlink"` (comma-separated)

## Usage

Run the main script:
```bash
python main.py --config config.toml
```

Or use default config:
```bash
python main.py
```

## Input Formats

### Serial Input
Binary format from RTK-DW1000 (automatically parsed).

### MQTT/UDP/File Input
JSON format:
```json
{
  "1": 2.5,
  "2": 3.1,
  "3": 2.8
}
```

Or array format:
```json
[
  {"id": 1, "distance": 2.5},
  {"id": 2, "distance": 3.1},
  {"id": 3, "distance": 2.8}
]
```

## Output Formats

### MAVLink
Sends `LOCAL_POSITION_NED` messages.

### MAVROS
Publishes to `mavros/fake_gps/mocap/pose` (ROS2 PoseStamped).

### UDP/File/Console
JSON format:
```json
{
  "position": {"x": 1.2, "y": 0.8, "z": 0.5},
  "timestamp": 1234567890.123
}
```

## Architecture

```
┌─────────────┐
│   Input     │  (Serial/MQTT/UDP/File)
│   Adapter   │
└──────┬──────┘
       │ distances {anchor_id: distance}
       ▼
┌─────────────┐
│ Localization│  (Multilateration Algorithm)
│   Engine    │
└──────┬──────┘
       │ position (x, y, z)
       ▼
┌─────────────┐
│   Output    │  (MAVLink/MAVROS/UDP/File/Console)
│   Adapter   │
└─────────────┘
```

## Extending

### Adding a New Input Adapter

1. Create a class inheriting from `InputAdapter`:
```python
class MyInputAdapter(InputAdapter):
    def start(self, callback):
        # Start receiving data
        pass
    
    def stop(self):
        # Stop receiving data
        pass
    
    def is_running(self):
        return self.running
```

2. Update `main.py` to support it in `_create_input_adapter()`.

### Adding a New Output Adapter

1. Create a class inheriting from `OutputAdapter`:
```python
class MyOutputAdapter(OutputAdapter):
    def send_position(self, position, timestamp=None):
        # Send position data
        pass
    
    def close(self):
        # Cleanup
        pass
```

2. Update `main.py` to support it in `_create_output_adapter()`.

## CI/CD

The project includes GitHub Actions workflows for:

- **Continuous Integration**: Runs tests on multiple Python versions (3.8-3.12)
- **Code Quality**: Runs linting and type checking
- **Coverage**: Uploads coverage reports to Codecov
- **Release**: Automatically builds and publishes to PyPI on version tags

Workflows are located in `.github/workflows/`.

## Development

### Running Tests Locally

```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=uwb_localizer --cov-report=html
```

### Code Quality

```bash
# Format code
black uwb_localizer/ tests/ main.py

# Lint code
flake8 uwb_localizer/ tests/ main.py
pylint uwb_localizer/ tests/ main.py
```

### Project Structure

```
uwb_node/
├── main.py                    # Main entry point
├── config.toml               # Configuration file
├── requirements.txt          # Dependencies
├── pytest.ini               # Pytest configuration
├── Makefile                 # Convenience commands
├── uwb_localizer/           # Core package
│   ├── __init__.py
│   ├── core.py              # Localization engine
│   ├── input_adapters.py    # Input adapters
│   └── output_adapters.py   # Output adapters
├── tests/                   # Test suite
│   ├── conftest.py          # Shared fixtures
│   ├── test_core.py          # Core tests
│   ├── test_input_adapters.py
│   ├── test_output_adapters.py
│   └── test_integration.py
└── .github/workflows/        # CI/CD pipelines
    ├── ci.yml               # Continuous integration
    └── release.yml          # Release automation
```

## License

See LICENSE file.
