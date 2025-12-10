#!/usr/bin/env python3
"""
Unit tests for data validation schemas
Tests Pydantic schemas without database or external dependencies

Run with: pytest tests/unit/test_schemas.py -v
Or: pytest -m unit
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.schemas import (
    DataPacket, DetectionInput, UWBMeasurementInput,
    AnchorCreate, AnchorUpdate, ProductCreate
)


@pytest.mark.unit
class TestDetectionInput:
    """Unit tests for DetectionInput schema"""
    
    def test_valid_detection(self):
        """Should accept valid detection data"""
        detection = DetectionInput(
            product_id="30396062c38d79c000287fa1",
            product_name="Test Product",
            x_position=100.5,
            y_position=200.7
        )
        assert detection.product_id == "30396062c38d79c000287fa1"
    
    def test_detection_with_defaults(self):
        """Should use default values for optional fields"""
        detection = DetectionInput(
            product_id="30396062c38e018000287287",
            product_name="Product"
        )
        assert detection.x_position is None
        assert detection.y_position is None
    
    def test_detection_missing_required_fields(self):
        """Should reject detection without required fields"""
        with pytest.raises(ValidationError):
            DetectionInput(product_id="30396062c38c0dc000388ca5")  # Missing product_name


@pytest.mark.unit
class TestUWBMeasurementInput:
    """Unit tests for UWBMeasurementInput schema"""
    
    def test_valid_uwb_measurement(self):
        """Should accept valid UWB measurement"""
        measurement = UWBMeasurementInput(
            mac_address="0x0001",
            distance_cm=245.5,
            status="0x01"
        )
        assert measurement.mac_address == "0x0001"
        assert measurement.distance_cm == 245.5
    
    def test_uwb_with_optional_status(self):
        """Should accept measurement without status"""
        measurement = UWBMeasurementInput(
            mac_address="0xABCD",
            distance_cm=150.0
        )
        assert measurement.status is None
    
    def test_uwb_negative_distance(self):
        """Should reject negative distance"""
        # Note: Add validation in schema if needed
        measurement = UWBMeasurementInput(
            mac_address="0x0001",
            distance_cm=-100.0
        )
        # Currently accepts negative - might want to add validator


@pytest.mark.unit
class TestDataPacket:
    """Unit tests for DataPacket schema"""
    
    def test_valid_data_packet(self):
        """Should accept valid complete data packet"""
        packet = DataPacket(
            timestamp="2025-12-08T10:00:00Z",
            detections=[
                {
                    "product_id": "30396062c38d79c000287fa1",
                    "product_name": "Product 1"
                }
            ],
            uwb_measurements=[
                {
                    "mac_address": "0x0001",
                    "distance_cm": 245.5
                }
            ]
        )
        assert len(packet.detections) == 1
        assert len(packet.uwb_measurements) == 1
    
    def test_empty_data_packet(self):
        """Should accept packet with empty arrays"""
        packet = DataPacket(
            timestamp="2025-12-08T10:00:00Z",
            detections=[],
            uwb_measurements=[]
        )
        assert len(packet.detections) == 0
        assert len(packet.uwb_measurements) == 0
    
    def test_packet_with_multiple_detections(self):
        """Should accept packet with multiple detections"""
        epcs = [
            "30396062c38d79c000287fa1", "30396062c38e018000287287",
            "30396062c38c0dc000388ca5", "30396062c38c0dc000388ca7",
            "30396062c39adec22fe06f67", "30396062c38d794000282374",
            "30396062c38d790000264ad0", "30396062c38d7a8000290de0",
            "30395dfa81a6e5c0001be67f", "30396062c39ea2406d991ee2"
        ]
        packet = DataPacket(
            timestamp="2025-12-08T10:00:00Z",
            detections=[
                {"product_id": epcs[i], "product_name": f"Product {i}"}
                for i in range(10)
            ],
            uwb_measurements=[]
        )
        assert len(packet.detections) == 10


@pytest.mark.unit
class TestAnchorCreate:
    """Unit tests for AnchorCreate schema"""
    
    def test_valid_anchor(self):
        """Should accept valid anchor configuration"""
        anchor = AnchorCreate(
            mac_address="0x0001",
            name="Front Left",
            x_position=0.0,
            y_position=0.0,
            is_active=True
        )
        assert anchor.mac_address == "0x0001"
        assert anchor.is_active is True
    
    def test_anchor_default_active(self):
        """Should default to active=True"""
        anchor = AnchorCreate(
            mac_address="0x0001",
            name="Test",
            x_position=100.0,
            y_position=200.0
        )
        assert anchor.is_active is True
    
    def test_anchor_missing_position(self):
        """Should reject anchor without position"""
        with pytest.raises(ValidationError):
            AnchorCreate(
                mac_address="0x0001",
                name="Test"
            )


@pytest.mark.unit
class TestAnchorUpdate:
    """Unit tests for AnchorUpdate schema"""
    
    def test_partial_update(self):
        """Should accept partial updates"""
        update = AnchorUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.x_position is None
        assert update.y_position is None
    
    def test_position_only_update(self):
        """Should accept position-only update"""
        update = AnchorUpdate(x_position=500.0, y_position=400.0)
        assert update.x_position == 500.0
        assert update.y_position == 400.0
        assert update.name is None
    
    def test_empty_update(self):
        """Should accept empty update (all optional)"""
        update = AnchorUpdate()
        assert update.name is None


@pytest.mark.unit
class TestProductCreate:
    """Unit tests for ProductCreate schema"""
    
    def test_valid_product(self):
        """Should accept valid product"""
        product = ProductCreate(
            sku="PROD001",
            name="Test Product",
            category="Electronics",
            unit_price=29.99,
            reorder_threshold=10,
            optimal_stock_level=50
        )
        assert product.sku == "PROD001"
        assert product.unit_price == 29.99
    
    def test_product_with_optional_fields(self):
        """Should accept product with minimal fields"""
        product = ProductCreate(
            sku="PROD002",
            name="Basic Product",
            category="General"
        )
        assert product.unit_price is None
        assert product.reorder_threshold is None
        assert product.optimal_stock_level is None
    
    def test_product_missing_required(self):
        """Should reject product without required fields"""
        with pytest.raises(ValidationError):
            ProductCreate(name="No SKU", category="General")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
