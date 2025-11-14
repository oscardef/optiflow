#!/usr/bin/env python3
"""Quick system test to verify OptiFlow is working"""
import requests
import json
from datetime import datetime

def test_system():
    print("\n" + "="*60)
    print("🧪 OPTIFLOW SYSTEM TEST")
    print("="*60 + "\n")
    
    # Test backend
    try:
        r = requests.get('http://localhost:8000/', timeout=2)
        data = r.json()
        print(f"✅ Backend: {data['status']}")
    except Exception as e:
        print(f"❌ Backend: {e}")
        return
    
    # Test anchors
    try:
        r = requests.get('http://localhost:8000/anchors', timeout=2)
        anchors = r.json()
        print(f"✅ Anchors: {len(anchors)} configured")
    except Exception as e:
        print(f"❌ Anchors: {e}")
    
    # Test positions
    try:
        r = requests.get('http://localhost:8000/positions/latest?limit=1', timeout=2)
        positions = r.json()
        if positions:
            pos = positions[0]
            ts = datetime.fromisoformat(pos['timestamp'])
            age = (datetime.now() - ts.replace(tzinfo=None)).total_seconds()
            print(f"✅ Positions: Latest {age:.1f}s ago")
            print(f"   Tag: {pos['tag_id']} at ({pos['x_position']:.1f}, {pos['y_position']:.1f})")
            
            if age < 5:
                print("   🎉 REAL-TIME DATA FLOWING!")
            elif age < 60:
                print("   ⚠️  Data is recent but not real-time")
            else:
                print("   ❌ Data is stale - simulator may not be running")
        else:
            print("❌ Positions: No data")
    except Exception as e:
        print(f"❌ Positions: {e}")
    
    # Test detections
    try:
        r = requests.get('http://localhost:8000/data/latest?limit=10', timeout=2)
        data = r.json()
        detections = data.get('detections', [])
        items = [d for d in detections if d.get('x_position')]
        print(f"✅ Detections: {len(items)} items with positions")
        if items:
            item = items[0]
            print(f"   Latest: {item['product_name']} - {item['status']}")
    except Exception as e:
        print(f"❌ Detections: {e}")
    
    print("\n" + "="*60)
    print("📱 Open http://localhost:3000 in your browser")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_system()
