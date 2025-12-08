#!/usr/bin/env python3
"""
Integration test for complete system flow
Tests data flow from MQTT → Backend → Database
Requires: Docker services running (docker compose up)

Run with: pytest tests/integration/test_system.py -v
Or: pytest -m integration
"""

import pytest
import requests
import time
import json
from datetime import datetime


API_BASE_URL = "http://localhost:8000"
TIMEOUT = 5


@pytest.mark.integration
class TestSystemIntegration:
    """Integration tests for complete data flow"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test"""
        # Setup: Clear existing data
        try:
            requests.delete(f"{API_BASE_URL}/data/clear", timeout=TIMEOUT)
        except:
            pytest.skip("Backend not available. Run: docker compose up")
        
        yield
        
        # Teardown: Clean up test data
        try:
            requests.delete(f"{API_BASE_URL}/data/clear", timeout=TIMEOUT)
        except:
            pass
    
    def test_backend_health(self):
        """Backend should be accessible"""
        response = requests.get(f"{API_BASE_URL}/docs", timeout=TIMEOUT)
        assert response.status_code == 200
    
    def test_data_ingestion_flow(self):
        """Should accept and store data packet"""
        # Create test data packet
        packet = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "detections": [
                {
                    "product_id": "30396062c38d794000282373",
                    "product_name": "Test Product",
                    "status": "present",
                    "x_position": 500.0,
                    "y_position": 400.0
                }
            ],
            "uwb_measurements": [
                {"mac_address": "0x0001", "distance_cm": 245.5},
                {"mac_address": "0x0002", "distance_cm": 312.0}
            ]
        }
        
        # Send to backend
        response = requests.post(
            f"{API_BASE_URL}/data",
            json=packet,
            timeout=TIMEOUT
        )
        
        assert response.status_code == 201
        result = response.json()
        assert result["detections_stored"] == 1
        assert result["uwb_measurements_stored"] == 2
    
    def test_anchor_configuration_and_triangulation(self):
        """Should configure anchors and calculate position"""
        # Create anchors
        anchors = [
            {"mac_address": "0x0001", "name": "Anchor 1", "x_position": 0, "y_position": 0},
            {"mac_address": "0x0002", "name": "Anchor 2", "x_position": 1000, "y_position": 0},
            {"mac_address": "0x0003", "name": "Anchor 3", "x_position": 1000, "y_position": 800},
            {"mac_address": "0x0004", "name": "Anchor 4", "x_position": 0, "y_position": 800}
        ]
        
        for anchor in anchors:
            response = requests.post(f"{API_BASE_URL}/anchors", json=anchor, timeout=TIMEOUT)
            assert response.status_code == 201
        
        # Send UWB measurements
        packet = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "detections": [],
            "uwb_measurements": [
                {"mac_address": "0x0001", "distance_cm": 640},
                {"mac_address": "0x0002", "distance_cm": 640},
                {"mac_address": "0x0003", "distance_cm": 640},
                {"mac_address": "0x0004", "distance_cm": 640}
            ]
        }
        
        response = requests.post(f"{API_BASE_URL}/data", json=packet, timeout=TIMEOUT)
        assert response.status_code == 201
        result = response.json()
        
        # Should calculate position
        assert result["position_calculated"] is True
        assert "calculated_position" in result
        
        # Verify position was stored
        positions = requests.get(f"{API_BASE_URL}/positions/latest?limit=1", timeout=TIMEOUT)
        assert positions.status_code == 200
        assert len(positions.json()) == 1
    
    def test_inventory_item_lifecycle(self):
        """Should track item from detection to missing"""
        # Detect item as present
        packet = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "detections": [
                {
                    "product_id": "30396062c39adec22fe06f68",
                    "product_name": "Lifecycle Product",
                    "status": "present",
                    "x_position": 300.0,
                    "y_position": 200.0
                }
            ],
            "uwb_measurements": []
        }
        
        response = requests.post(f"{API_BASE_URL}/data", json=packet, timeout=TIMEOUT)
        assert response.status_code == 201
        
        # Check item exists
        items = requests.get(f"{API_BASE_URL}/data/items", timeout=TIMEOUT)
        assert items.status_code == 200
        item_list = items.json()
        assert len(item_list) > 0
        
        # Find our test item
        test_item = next((i for i in item_list if i["product_id"] == "30396062c39adec22fe06f68"), None)
        assert test_item is not None
        assert test_item["status"] == "present"
        
        # Mark item as not present
        packet["detections"][0]["status"] = "not present"
        response = requests.post(f"{API_BASE_URL}/data", json=packet, timeout=TIMEOUT)
        assert response.status_code == 201
        
        # Verify item is now missing
        missing_items = requests.get(f"{API_BASE_URL}/data/missing", timeout=TIMEOUT)
        assert missing_items.status_code == 200
        missing_list = missing_items.json()
        test_missing = next((i for i in missing_list if i["product_id"] == "30396062c39adec22fe06f68"), None)
        assert test_missing is not None
        assert test_missing["status"] == "not present"
    
    def test_mode_switching(self):
        """Should switch between simulation and production modes"""
        # Get current mode
        response = requests.get(f"{API_BASE_URL}/config/mode", timeout=TIMEOUT)
        assert response.status_code == 200
        current_mode = response.json()["mode"]
        
        # Switch mode
        new_mode = "production" if current_mode == "simulation" else "simulation"
        response = requests.post(
            f"{API_BASE_URL}/config/mode/switch",
            json={"mode": new_mode},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        
        # Verify mode changed
        response = requests.get(f"{API_BASE_URL}/config/mode", timeout=TIMEOUT)
        assert response.json()["mode"] == new_mode
        
        # Switch back
        response = requests.post(
            f"{API_BASE_URL}/config/mode/switch",
            json={"mode": current_mode},
            timeout=TIMEOUT
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
