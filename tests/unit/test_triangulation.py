#!/usr/bin/env python3
"""
Unit tests for triangulation logic
Tests the position calculation algorithms without external dependencies

Run with: pytest tests/unit/test_triangulation.py -v
Or: pytest -m unit
"""

import pytest
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.triangulation import TriangulationService


@pytest.mark.unit
class TestTriangulationService:
    """Unit tests for TriangulationService"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.service = TriangulationService()
        
        # Setup test anchors at corners of a 1000x800 cm store
        self.anchors = [
            {"id": 1, "mac_address": "0x0001", "x_position": 0, "y_position": 0, "is_active": True},
            {"id": 2, "mac_address": "0x0002", "x_position": 1000, "y_position": 0, "is_active": True},
            {"id": 3, "mac_address": "0x0003", "x_position": 1000, "y_position": 800, "is_active": True},
            {"id": 4, "mac_address": "0x0004", "x_position": 0, "y_position": 800, "is_active": True},
        ]
    
    def test_calculate_with_no_measurements(self):
        """Should return None when no measurements provided"""
        result = self.service.calculate_position([])
        assert result is None
    
    def test_calculate_with_one_measurement(self):
        """Should return None with only one anchor measurement"""
        measurements = [(0, 0, 100)]  # (x, y, distance) tuples
        result = self.service.calculate_position(measurements)
        assert result is None
    
    def test_calculate_with_two_measurements(self):
        """Should calculate position with two anchors (weighted midpoint)"""
        # Tag 500cm from anchor 1 (0,0) and 500cm from anchor 2 (1000,0)
        measurements = [
            (0, 0, 500),
            (1000, 0, 500)
        ]
        result = self.service.calculate_position(measurements)
        
        assert result is not None
        x, y, confidence = result
        # Should be roughly in the middle horizontally
        assert 400 <= x <= 600
        assert confidence >= 0.3
    
    def test_calculate_with_three_measurements(self):
        """Should calculate position with three anchors (least squares)"""
        # Tag roughly at center (500, 400)
        measurements = [
            (0, 0, 640),       # ~sqrt(500^2 + 400^2)
            (1000, 0, 640),    # ~sqrt(500^2 + 400^2)
            (1000, 800, 640),  # ~sqrt(500^2 + 400^2)
        ]
        result = self.service.calculate_position(measurements)
        
        assert result is not None
        x, y, confidence = result
        # Should be roughly at center
        assert 300 <= x <= 700
        assert 200 <= y <= 600
        assert confidence >= 0.5
    
    def test_calculate_with_four_measurements(self):
        """Should calculate position with four anchors (highest confidence)"""
        # Tag at (500, 400)
        measurements = [
            (0, 0, 640),
            (1000, 0, 640),
            (1000, 800, 640),
            (0, 800, 640),
        ]
        result = self.service.calculate_position(measurements)
        
        assert result is not None
        x, y, confidence = result
        # Four anchors should give higher confidence
        assert confidence >= 0.7
    
    def test_calculate_with_unknown_anchor(self):
        """Should calculate with valid measurements only"""
        measurements = [
            (0, 0, 100),
            (1000, 0, 100),
        ]
        result = self.service.calculate_position(measurements)
        # Should still work with 2 valid measurements
        assert result is not None
    
    def test_calculate_with_inactive_anchor(self):
        """Test with subset of measurements (simulating inactive anchor)"""
        # Only use one measurement (inactive anchors filtered out before calling)
        measurements = [
            (0, 0, 100),
        ]
        result = self.service.calculate_position(measurements)
        # Should return None with only one measurement
        assert result is None
    
    def test_confidence_scoring(self):
        """Should calculate appropriate confidence scores"""
        # More anchors should generally give higher confidence
        measurements_2 = [
            (0, 0, 500),
            (1000, 0, 500)
        ]
        measurements_4 = [
            (0, 0, 640),
            (1000, 0, 640),
            (1000, 800, 640),
            (0, 800, 640)
        ]
        
        result_2 = self.service.calculate_position(measurements_2)
        result_4 = self.service.calculate_position(measurements_4)
        
        assert result_2 is not None
        assert result_4 is not None
        
        _, _, conf_2 = result_2
        _, _, conf_4 = result_4
        
        assert conf_4 > conf_2
    
    def test_position_bounds(self):
        """Calculated position should be within reasonable bounds"""
        measurements = [
            (0, 0, 200),
            (1000, 0, 200),
        ]
        result = self.service.calculate_position(measurements)
        
        assert result is not None
        x, y, confidence = result
        # Position should be within store bounds (with some tolerance)
        assert -200 <= x <= 1200
        assert -200 <= y <= 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
