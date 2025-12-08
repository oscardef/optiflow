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
        result = self.service.calculate_position([], self.anchors, tag_id="test")
        assert result is None
    
    def test_calculate_with_one_measurement(self):
        """Should return None with only one anchor measurement"""
        measurements = [
            {"mac_address": "0x0001", "distance_cm": 100}
        ]
        result = self.service.calculate_position(measurements, self.anchors, tag_id="test")
        assert result is None
    
    def test_calculate_with_two_measurements(self):
        """Should calculate position with two anchors (weighted midpoint)"""
        # Tag 500cm from anchor 1 (0,0) and 500cm from anchor 2 (1000,0)
        measurements = [
            {"mac_address": "0x0001", "distance_cm": 500},
            {"mac_address": "0x0002", "distance_cm": 500}
        ]
        result = self.service.calculate_position(measurements, self.anchors, tag_id="test")
        
        assert result is not None
        assert result["tag_id"] == "test"
        # Should be roughly in the middle horizontally
        assert 400 <= result["x_position"] <= 600
        assert result["confidence"] >= 0.3
        assert result["num_anchors"] == 2
    
    def test_calculate_with_three_measurements(self):
        """Should calculate position with three anchors (least squares)"""
        # Tag roughly at center (500, 400)
        measurements = [
            {"mac_address": "0x0001", "distance_cm": 640},  # ~sqrt(500^2 + 400^2)
            {"mac_address": "0x0002", "distance_cm": 640},  # ~sqrt(500^2 + 400^2)
            {"mac_address": "0x0003", "distance_cm": 640},  # ~sqrt(500^2 + 400^2)
        ]
        result = self.service.calculate_position(measurements, self.anchors, tag_id="test")
        
        assert result is not None
        assert result["tag_id"] == "test"
        # Should be roughly at center
        assert 300 <= result["x_position"] <= 700
        assert 200 <= result["y_position"] <= 600
        assert result["confidence"] >= 0.5
        assert result["num_anchors"] == 3
    
    def test_calculate_with_four_measurements(self):
        """Should calculate position with four anchors (highest confidence)"""
        # Tag at (500, 400)
        measurements = [
            {"mac_address": "0x0001", "distance_cm": 640},
            {"mac_address": "0x0002", "distance_cm": 640},
            {"mac_address": "0x0003", "distance_cm": 640},
            {"mac_address": "0x0004", "distance_cm": 640},
        ]
        result = self.service.calculate_position(measurements, self.anchors, tag_id="test")
        
        assert result is not None
        assert result["num_anchors"] == 4
        # Four anchors should give higher confidence
        assert result["confidence"] >= 0.7
    
    def test_calculate_with_unknown_anchor(self):
        """Should ignore measurements from unknown anchors"""
        measurements = [
            {"mac_address": "0x0001", "distance_cm": 100},
            {"mac_address": "0x9999", "distance_cm": 100},  # Unknown anchor
        ]
        result = self.service.calculate_position(measurements, self.anchors, tag_id="test")
        # Should ignore unknown anchor and return None (only 1 valid measurement)
        assert result is None
    
    def test_calculate_with_inactive_anchor(self):
        """Should ignore measurements from inactive anchors"""
        inactive_anchors = self.anchors.copy()
        inactive_anchors[1] = {**inactive_anchors[1], "is_active": False}
        
        measurements = [
            {"mac_address": "0x0001", "distance_cm": 100},
            {"mac_address": "0x0002", "distance_cm": 100},  # Inactive anchor
        ]
        result = self.service.calculate_position(measurements, inactive_anchors, tag_id="test")
        # Should ignore inactive anchor and return None
        assert result is None
    
    def test_confidence_scoring(self):
        """Should calculate appropriate confidence scores"""
        # More anchors should generally give higher confidence
        measurements_2 = [
            {"mac_address": "0x0001", "distance_cm": 500},
            {"mac_address": "0x0002", "distance_cm": 500}
        ]
        measurements_4 = [
            {"mac_address": "0x0001", "distance_cm": 640},
            {"mac_address": "0x0002", "distance_cm": 640},
            {"mac_address": "0x0003", "distance_cm": 640},
            {"mac_address": "0x0004", "distance_cm": 640}
        ]
        
        result_2 = self.service.calculate_position(measurements_2, self.anchors, tag_id="test")
        result_4 = self.service.calculate_position(measurements_4, self.anchors, tag_id="test")
        
        assert result_2 is not None
        assert result_4 is not None
        assert result_4["confidence"] > result_2["confidence"]
    
    def test_position_bounds(self):
        """Calculated position should be within reasonable bounds"""
        measurements = [
            {"mac_address": "0x0001", "distance_cm": 200},
            {"mac_address": "0x0002", "distance_cm": 200},
        ]
        result = self.service.calculate_position(measurements, self.anchors, tag_id="test")
        
        assert result is not None
        # Position should be within store bounds (with some tolerance)
        assert -200 <= result["x_position"] <= 1200
        assert -200 <= result["y_position"] <= 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
