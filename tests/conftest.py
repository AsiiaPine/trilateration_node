"""
Shared pytest fixtures and configuration.
"""
import pytest
import math
from uwb_localizer import LocalizationEngine


@pytest.fixture
def standard_anchors():
    """Standard anchor positions for testing."""
    return {
        1: (0.0, 0.0, 0.0),
        2: (3.0, 0.0, 0.0),
        3: (0.0, 3.0, 0.0)
    }


@pytest.fixture
def standard_engine(standard_anchors):
    """Standard localization engine for testing."""
    return LocalizationEngine(
        anchor_positions=standard_anchors,
        calibration_type='none',
        calibration_params=[],
        z_sign=0,
        min_range=0.0,
        max_range=100.0
    )


@pytest.fixture
def test_distances():
    """Test distance measurements for point at (1, 1, 0)."""
    return {
        1: math.sqrt(2),  # Distance to (0,0,0)
        2: math.sqrt(5),  # Distance to (3,0,0)
        3: math.sqrt(5)   # Distance to (0,3,0)
    }


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file path."""
    return tmp_path / "test_file.json"
