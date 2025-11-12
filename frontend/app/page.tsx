'use client';

import { useState, useEffect } from 'react';
import StoreMap from './components/StoreMap';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Anchor {
  id: number;
  mac_address: string;
  name: string;
  x_position: number;
  y_position: number;
  is_active: boolean;
}

interface Position {
  id: number;
  tag_id: string;
  x_position: number;
  y_position: number;
  confidence: number;
  timestamp: string;
  num_anchors: number;
}

export default function Home() {
  const [setupMode, setSetupMode] = useState(false);
  const [anchors, setAnchors] = useState<Anchor[]>([]);
  const [positions, setPositions] = useState<TagPosition[]>([]);
  const [selectedAnchor, setSelectedAnchor] = useState<Anchor | null>(null);
  const [isSetupMode, setIsSetupMode] = useState(false);
  const [editingAnchorId, setEditingAnchorId] = useState<string | null>(null);
  const [items, setItems] = useState<Array<{
    product_id: string;
    product_name: string;
    x_position: number;
    y_position: number;
    status: string;
  }>>([]);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);

  // Fetch anchors from backend
  const fetchAnchors = async () => {
    try {
      const response = await fetch('http://localhost:8000/anchors');
      const data = await response.json();
      setAnchors(data);
    } catch (error) {
      console.error('Error fetching anchors:', error);
    }
  };

  // Fetch latest positions
  const fetchPositions = async () => {
    try {
      const response = await fetch('http://localhost:8000/positions/latest');
      const data = await response.json();
      setPositions(data);
    } catch (error) {
      console.error('Error fetching positions:', error);
    }
  };

  // Fetch items from detections
  const fetchItems = async () => {
    try {
      const response = await fetch('http://localhost:8000/data/latest?limit=100');
      const data = await response.json();
      
      // Group detections by product_id to get unique items with latest status
      const itemMap = new Map();
      data.forEach((detection: any) => {
        if (detection.x_position && detection.y_position) {
          const existing = itemMap.get(detection.product_id);
          // Keep the most recent detection
          if (!existing || new Date(detection.timestamp) > new Date(existing.timestamp)) {
            itemMap.set(detection.product_id, {
              product_id: detection.product_id,
              product_name: detection.product_name,
              x_position: detection.x_position,
              y_position: detection.y_position,
              status: detection.status || 'present',
            });
          }
        }
      });
      
      setItems(Array.from(itemMap.values()));
    } catch (error) {
      console.error('Error fetching items:', error);
    }
  };  // Initial load
  useEffect(() => {
    const init = async () => {
      await fetchAnchors();
      await fetchPositions();
      await fetchItems();
      setLoading(false);
    };
    init();
  }, []);

  // Auto-refresh positions and items when not in setup mode
  useEffect(() => {
    if (setupMode) return;
    
    const interval = setInterval(() => {
      fetchPositions();
      fetchItems();
    }, 2000); // Refresh every 2 seconds
    
    return () => clearInterval(interval);
  }, [setupMode]);

  // Create anchor
  const handleAnchorPlace = async (x: number, y: number, index: number) => {
    const anchorData = {
      mac_address: `0x000${index + 1}`,
      name: `Anchor ${index + 1}`,
      x_position: Math.round(x),
      y_position: Math.round(y),
      is_active: true
    };

    try {
      const response = await fetch(`${API_URL}/anchors`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(anchorData)
      });

      if (response.ok) {
        await fetchAnchors();
      } else {
        const error = await response.json();
        alert(`Failed to create anchor: ${error.detail}`);
      }
    } catch (error) {
      console.error('Failed to create anchor:', error);
      alert('Failed to create anchor. Check console for details.');
    }
  };

  // Update anchor position
  const handleAnchorUpdate = async (anchorId: number, x: number, y: number) => {
    try {
      const response = await fetch(`${API_URL}/anchors/${anchorId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          x_position: Math.round(x),
          y_position: Math.round(y)
        })
      });

      if (response.ok) {
        await fetchAnchors();
      }
    } catch (error) {
      console.error('Failed to update anchor:', error);
    }
  };

  // Delete all anchors (reset)
  const handleResetAnchors = async () => {
    if (!confirm('Delete all anchors? This cannot be undone.')) return;

    try {
      for (const anchor of anchors) {
        await fetch(`${API_URL}/anchors/${anchor.id}`, { method: 'DELETE' });
      }
      await fetchAnchors();
    } catch (error) {
      console.error('Failed to reset anchors:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-2xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-8">
      <header className="mb-8">
        <h1 className="text-4xl font-bold mb-2">🏪 OptiFlow</h1>
        <p className="text-slate-400">Real-time Store Tracking System</p>
        
        <div className="mt-4 flex items-center gap-4">
          <div className={`px-4 py-2 rounded-lg ${connected ? 'bg-green-900/30 border border-green-700' : 'bg-red-900/30 border border-red-700'}`}>
            <span className="mr-2">Backend:</span>
            <span className={`font-semibold ${connected ? 'text-green-400' : 'text-red-400'}`}>
              ● {connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          
          <div className="px-4 py-2 rounded-lg bg-slate-800 border border-slate-700">
            <span className="mr-2">Anchors:</span>
            <span className="font-semibold text-blue-400">
              {anchors.filter(a => a.is_active).length} active
            </span>
          </div>
          
          <div className="px-4 py-2 rounded-lg bg-slate-800 border border-slate-700">
            <span className="mr-2">Tags:</span>
            <span className="font-semibold text-green-400">
              {new Set(positions.map(p => p.tag_id)).size} tracked
            </span>
          </div>
        </div>
      </header>

      <div className="mb-6 flex gap-4">
        <button
          onClick={() => setSetupMode(!setupMode)}
          className={`btn-primary ${setupMode ? 'bg-orange-500 hover:bg-orange-600' : ''}`}
        >
          {setupMode ? '✓ Finish Setup' : '⚙️ Setup Mode'}
        </button>
        
        {setupMode && (
          <>
            <button
              onClick={handleResetAnchors}
              className="btn-secondary bg-red-700 hover:bg-red-600"
            >
              🗑️ Reset Anchors
            </button>
            
            <div className="ml-auto text-sm text-slate-400 flex items-center">
              <div className="bg-slate-800 px-4 py-2 rounded-lg">
                💡 Click on the map to place anchors at their physical locations.<br/>
                Drag anchors to reposition them.
              </div>
            </div>
          </>
        )}
        
        {!setupMode && (
          <button
            onClick={fetchPositions}
            className="btn-secondary"
          >
            🔄 Refresh
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div className="xl:col-span-2">
          <div className="bg-slate-800 p-6 rounded-lg">
            <h2 className="text-2xl font-semibold mb-4">Store Map</h2>
            <StoreMap
              anchors={anchors}
              positions={positions}
              items={items}
              setupMode={setupMode}
              onAnchorPlace={handleAnchorPlace}
              onAnchorUpdate={handleAnchorUpdate}
            />
          </div>
        </div>

        <div className="space-y-6">
          {/* Missing Items Alert */}
          {items.filter(item => item.status === 'missing').length > 0 && (
            <div className="bg-red-900/30 border border-red-500 p-6 rounded-lg">
              <h2 className="text-xl font-semibold mb-4 text-red-400 flex items-center gap-2">
                <span>⚠️</span>
                Missing Items ({items.filter(item => item.status === 'missing').length})
              </h2>
              <div className="space-y-2">
                {items
                  .filter(item => item.status === 'missing')
                  .slice(0, 5)
                  .map(item => (
                    <div
                      key={item.product_id}
                      className="p-3 bg-slate-800 rounded border border-red-500/30"
                    >
                      <div className="font-semibold text-red-300">{item.product_name}</div>
                      <div className="text-xs text-slate-400 mt-1">
                        ID: {item.product_id}
                      </div>
                      <div className="text-xs text-slate-400">
                        Last seen: ({Math.round(item.x_position)}cm, {Math.round(item.y_position)}cm)
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Anchor List */}
          <div className="bg-slate-800 p-6 rounded-lg">
            <h2 className="text-xl font-semibold mb-4">Anchors ({anchors.length})</h2>
            
            {anchors.length === 0 ? (
              <p className="text-slate-400 text-sm">
                No anchors configured. Enable Setup Mode to add anchors.
              </p>
            ) : (
              <div className="space-y-3">
                {anchors.map(anchor => (
                  <div
                    key={anchor.id}
                    className="p-3 bg-slate-700 rounded border border-slate-600"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold">{anchor.name}</span>
                      <span className={`text-xs px-2 py-1 rounded ${anchor.is_active ? 'bg-green-900/50 text-green-300' : 'bg-gray-600 text-gray-300'}`}>
                        {anchor.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div className="text-sm text-slate-400">
                      <div>{anchor.mac_address}</div>
                      <div>Position: ({Math.round(anchor.x_position)}cm, {Math.round(anchor.y_position)}cm)</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Positions */}
          <div className="bg-slate-800 p-6 rounded-lg">
            <h2 className="text-xl font-semibold mb-4">Live Positions</h2>
            
            {positions.length === 0 ? (
              <p className="text-slate-400 text-sm">
                No position data yet. Start the ESP32 simulator or connect real hardware.
              </p>
            ) : (
              <div className="space-y-3">
                {positions.slice(0, 5).map(pos => (
                  <div
                    key={pos.id}
                    className="p-3 bg-slate-700 rounded border border-slate-600"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-green-400">{pos.tag_id}</span>
                      <span className="text-xs text-slate-400">
                        {new Date(pos.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="text-sm text-slate-400">
                      <div>Position: ({Math.round(pos.x_position)}cm, {Math.round(pos.y_position)}cm)</div>
                      <div className="flex items-center justify-between mt-1">
                        <span>Confidence: {(pos.confidence * 100).toFixed(0)}%</span>
                        <span>{pos.num_anchors} anchors</span>
                      </div>
                    </div>
                    
                    {/* Confidence bar */}
                    <div className="mt-2 w-full bg-slate-600 rounded-full h-1.5">
                      <div
                        className="bg-green-500 h-1.5 rounded-full transition-all"
                        style={{ width: `${pos.confidence * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick Start */}
          {anchors.length === 0 && (
            <div className="bg-blue-900/20 border border-blue-700 p-6 rounded-lg">
              <h3 className="text-lg font-semibold mb-3">🚀 Quick Start</h3>
              <ol className="text-sm space-y-2 text-slate-300">
                <li>1. Click "Setup Mode" above</li>
                <li>2. Click on the map to place 4 anchors at your physical anchor locations</li>
                <li>3. Click "Finish Setup"</li>
                <li>4. Run: <code className="bg-slate-800 px-2 py-1 rounded">python esp32_simulator.py</code></li>
                <li>5. Start data: <code className="bg-slate-800 px-2 py-1 rounded">mosquitto_pub -h 172.20.10.3 -t store/control -m START</code></li>
              </ol>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
