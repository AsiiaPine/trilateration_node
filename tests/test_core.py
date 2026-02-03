"""
Unit tests for core localization module.
"""
import pytest
import math
from uwb_localizer.core import (
    LocalizationEngine,
    multilateration,
    calibrated_linear,
    calibrated_quadratic,
    calibrated_cubic,
    solve_position
)


class TestCalibration:
    """Test calibration functions."""
    
    def test_linear_calibration(self):
        """Test linear calibration."""
        assert calibrated_linear(2.0, 1.0, 5.0) == 11.0  # 2*5 + 1
        assert calibrated_linear(1.0, 0.0, 10.0) == 10.0  # Identity
    
    def test_quadratic_calibration(self):
        """Test quadratic calibration."""
        # x^2 + 2x + 1 at x=2 should be 9
        assert calibrated_quadratic(1.0, 2.0, 1.0, 2.0) == 9.0
    
    def test_cubic_calibration(self):
        """Test cubic calibration."""
        # x^3 at x=2 should be 8
        assert calibrated_cubic(1.0, 0.0, 0.0, 0.0, 2.0) == 8.0


class TestTrilateration:
    """Test trilateration function."""
    
    def test_solve_position_simple(self):
        """Test simple trilateration with known solution."""
        # Anchors at (0,0,0), (3,0,0), (0,3,0)
        # Point at (1,1,0) should have distances: sqrt(2), sqrt(5), sqrt(5)
        d1 = math.sqrt(2)  # Distance to (0,0,0)
        d2 = math.sqrt(5)  # Distance to (3,0,0)
        d3 = math.sqrt(5)  # Distance to (0,3,0)
        
        x, y, z = solve_position(d1, d2, d3, z_sign=1, L2=3.0, L3=3.0)
        
        assert abs(x - 1.0) < 0.01
        assert abs(y - 1.0) < 0.01
        assert abs(z - 0.0) < 0.01
    
    def test_solve_position_3d(self):
        """Test 3D trilateration."""
        # Point at (1,1,1) with anchors at (0,0,0), (3,0,0), (0,3,0)
        d1 = math.sqrt(3)  # Distance to (0,0,0)
        d2 = math.sqrt(6)  # Distance to (3,0,0)
        d3 = math.sqrt(6)  # Distance to (0,3,0)
        
        x, y, z = solve_position(d1, d2, d3, z_sign=1, L2=3.0, L3=3.0)
        
        assert abs(x - 1.0) < 0.01
        assert abs(y - 1.0) < 0.01
        assert abs(z - 1.0) < 0.01


class TestMultilateration:
    """Test multilateration function."""
    
    def test_multilateration_sufficient_anchors(self):
        """Test multilateration with sufficient anchors."""
        anchor_positions = {
            1: (0.0, 0.0, 0.0),
            2: (3.0, 0.0, 0.0),
            3: (0.0, 3.0, 0.0)
        }
        
        # Point at (1,1,0)
        distances = {
            1: math.sqrt(2),
            2: math.sqrt(5),
            3: math.sqrt(5)
        }
        
        x, y, z = multilateration(distances, anchor_positions, z_sign=0)
        
        assert abs(x - 1.0) < 0.1
        assert abs(y - 1.0) < 0.1
        assert abs(z - 0.0) < 0.1
    
    def test_multilateration_insufficient_anchors(self):
        """Test multilateration fails with insufficient anchors."""
        anchor_positions = {
            1: (0.0, 0.0, 0.0),
            2: (3.0, 0.0, 0.0)
        }
        
        distances = {
            1: 1.0,
            2: 2.0
        }
        
        with pytest.raises(ValueError, match="Not enough anchor positions"):
            multilateration(distances, anchor_positions)
    
    def test_multilateration_insufficient_data(self):
        """Test multilateration fails with insufficient distance data."""
        anchor_positions = {
            1: (0.0, 0.0, 0.0),
            2: (3.0, 0.0, 0.0),
            3: (0.0, 3.0, 0.0)
        }
        
        distances = {
            1: 1.0,
            2: 2.0
        }
        
        with pytest.raises(ValueError, match="Not enough data"):
            multilateration(distances, anchor_positions)
    
    def test_multilateration_no_common_anchors(self):
        """Test multilateration fails when no common anchors."""
        anchor_positions = {
            1: (0.0, 0.0, 0.0),
            2: (3.0, 0.0, 0.0),
            3: (0.0, 3.0, 0.0)
        }
        
        distances = {
            4: 1.0,
            5: 2.0,
            6: 3.0
        }
        
        with pytest.raises(ValueError, match="Not enough common anchors"):
            multilateration(distances, anchor_positions)


class TestLocalizationEngine:
    """Test LocalizationEngine class."""
    
    @pytest.fixture
    def engine(self):
        """Create a test localization engine."""
        anchor_positions = {
            1: (0.0, 0.0, 0.0),
            2: (3.0, 0.0, 0.0),
            3: (0.0, 3.0, 0.0)
        }
        return LocalizationEngine(
            anchor_positions=anchor_positions,
            calibration_type='none',
            z_sign=0,
            min_range=0.0,
            max_range=100.0
        )
    
    def test_engine_initialization(self, engine):
        """Test engine initialization."""
        assert len(engine.anchor_positions) == 3
        assert engine.calibration_type == 'none'
    
    def test_engine_insufficient_anchors(self):
        """Test engine fails with insufficient anchors."""
        anchor_positions = {
            1: (0.0, 0.0, 0.0),
            2: (3.0, 0.0, 0.0)
        }
        
        with pytest.raises(ValueError, match="At least 3 anchor positions"):
            LocalizationEngine(anchor_positions=anchor_positions)
    
    def test_calibrate_none(self, engine):
        """Test no calibration."""
        assert engine.calibrate(5.0) == 5.0
    
    def test_calibrate_linear(self):
        """Test linear calibration."""
        anchor_positions = {1: (0, 0, 0), 2: (3, 0, 0), 3: (0, 3, 0)}
        engine = LocalizationEngine(
            anchor_positions=anchor_positions,
            calibration_type='linear',
            calibration_params=[2.0, 1.0]
        )
        assert engine.calibrate(5.0) == 11.0  # 2*5 + 1
    
    def test_calibrate_quadratic(self):
        """Test quadratic calibration."""
        anchor_positions = {1: (0, 0, 0), 2: (3, 0, 0), 3: (0, 3, 0)}
        engine = LocalizationEngine(
            anchor_positions=anchor_positions,
            calibration_type='quadratic',
            calibration_params=[1.0, 2.0, 1.0]
        )
        assert engine.calibrate(2.0) == 9.0  # 2^2 + 2*2 + 1
    
    def test_validate_range(self, engine):
        """Test range validation."""
        assert engine.validate_range(50.0) is True
        assert engine.validate_range(0.0) is True
        assert engine.validate_range(100.0) is True
        assert engine.validate_range(-1.0) is False
        assert engine.validate_range(101.0) is False
    
    def test_calculate_position_valid(self, engine):
        """Test position calculation with valid data."""
        distances = {
            1: math.sqrt(2),
            2: math.sqrt(5),
            3: math.sqrt(5)
        }
        
        position = engine.calculate_position(distances)
        assert position is not None
        assert len(position) == 3
        x, y, z = position
        assert abs(x - 1.0) < 0.1
        assert abs(y - 1.0) < 0.1
    
    def test_calculate_position_insufficient_data(self, engine):
        """Test position calculation with insufficient data."""
        distances = {
            1: 1.0,
            2: 2.0
        }
        
        position = engine.calculate_position(distances)
        assert position is None
    
    def test_calculate_position_out_of_range(self, engine):
        """Test position calculation filters out-of-range distances."""
        distances = {
            1: math.sqrt(2),
            2: math.sqrt(5),
            3: 150.0  # Out of range
        }
        
        position = engine.calculate_position(distances)
        # Should still work with 2 valid distances if algorithm allows
        # But multilateration requires 3, so should return None
        assert position is None
    
    def test_calculate_position_none_values(self, engine):
        """Test position calculation handles None values."""
        distances = {
            1: math.sqrt(2),
            2: None,
            3: math.sqrt(5)
        }
        
        position = engine.calculate_position(distances)
        assert position is None  # Not enough valid distances
