"""
Integration tests for the full localization system.
"""
import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
from uwb_localizer import LocalizationEngine
from uwb_localizer.input_adapters import FileInputAdapter
from uwb_localizer.output_adapters import FileOutputAdapter, ConsoleOutputAdapter


class TestEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.fixture
    def anchor_positions(self):
        """Standard anchor positions for testing."""
        return {
            1: (0.0, 0.0, 0.0),
            2: (3.0, 0.0, 0.0),
            3: (0.0, 3.0, 0.0)
        }
    
    @pytest.fixture
    def engine(self, anchor_positions):
        """Create localization engine."""
        return LocalizationEngine(
            anchor_positions=anchor_positions,
            calibration_type='none',
            z_sign=0,
            min_range=0.0,
            max_range=100.0
        )
    
    def test_file_input_file_output(self, engine, tmp_path):
        """Test file input to file output."""
        import math
        
        # Create input file with distance measurements
        input_file = tmp_path / "input.json"
        distances = {
            "1": math.sqrt(2),
            "2": math.sqrt(5),
            "3": math.sqrt(5)
        }
        with open(input_file, 'w') as f:
            json.dump(distances, f)
        
        # Create output file
        output_file = tmp_path / "output.jsonl"
        
        # Create adapters
        input_adapter = FileInputAdapter(str(input_file), poll_interval=0.1)
        output_adapter = FileOutputAdapter(str(output_file), mode='w')
        
        # Collect positions
        positions = []
        
        def on_distance(distances_dict):
            # Convert string keys to int keys
            int_distances = {int(k): float(v) for k, v in distances_dict.items()}
            position = engine.calculate_position(int_distances)
            if position:
                positions.append(position)
                output_adapter.send_position(position)
        
        # Start input adapter
        input_adapter.start(on_distance)
        
        # Wait for processing
        import time
        time.sleep(0.3)
        
        # Stop
        input_adapter.stop()
        output_adapter.close()
        
        # Verify position was calculated
        assert len(positions) > 0
        x, y, z = positions[0]
        assert abs(x - 1.0) < 0.1
        assert abs(y - 1.0) < 0.1
        
        # Verify output file was created
        assert output_file.exists()
        
        # Verify output file content
        with open(output_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) > 0
            data = json.loads(lines[0])
            assert 'position' in data
            assert abs(data['position']['x'] - 1.0) < 0.1
    
    def test_calibration_pipeline(self, anchor_positions):
        """Test calibration is applied correctly."""
        engine = LocalizationEngine(
            anchor_positions=anchor_positions,
            calibration_type='linear',
            calibration_params=[2.0, 1.0],  # 2*x + 1
            z_sign=0,
            min_range=0.0,
            max_range=100.0
        )
        
        # Raw distances (before calibration)
        raw_distances = {
            1: 1.0,  # After calibration: 2*1 + 1 = 3.0
            2: 2.0,  # After calibration: 2*2 + 1 = 5.0
            3: 1.5   # After calibration: 2*1.5 + 1 = 4.0
        }
        
        # Manually calibrate and calculate
        calibrated = {}
        for anchor_id, raw in raw_distances.items():
            calibrated[anchor_id] = engine.calibrate(raw)
        
        # Verify calibration
        assert calibrated[1] == 3.0
        assert calibrated[2] == 5.0
        assert calibrated[3] == 4.0
        
        # Calculate position with calibrated distances
        position = engine.calculate_position(calibrated)
        assert position is not None
    
    def test_range_filtering(self, engine):
        """Test that out-of-range distances are filtered."""
        import math
        
        distances = {
            1: math.sqrt(2),  # Valid
            2: math.sqrt(5),  # Valid
            3: 150.0  # Out of range (>100)
        }
        
        position = engine.calculate_position(distances)
        
        # Should return None because we don't have 3 valid distances
        assert position is None
        
        # With all valid distances, should work
        distances_valid = {
            1: math.sqrt(2),
            2: math.sqrt(5),
            3: math.sqrt(5)
        }
        
        position = engine.calculate_position(distances_valid)
        assert position is not None
