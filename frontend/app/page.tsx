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
  const [positions, setPositions] = useState<Position[]>([]);
  const [selectedAnchor, setSelectedAnchor] = useState<Anchor | null>(null);
  const [isSetupMode, setIsSetupMode] = useState(false);
  const [editingAnchorId, setEditingAnchorId] = useState<string | null>(null);
  const [items, setItems] = useState<Array<{
    product_id: string;
    product_name: string;
    x_position: number;
    y_position: number;
    status: string;
    timestamp?: string;
  }>>([]);
  const [missingItems, setMissingItems] = useState<Array<{
    product_id: string;
    product_name: string;
    x_position: number;
    y_position: number;
    status: string;
    timestamp?: string;
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

  // Fetch latest positions - show most recent position per tag
  const fetchPositions = async () => {
    try {
      const response = await fetch('http://localhost:8000/positions/latest?limit=100');
      const data = await response.json();
      
      // Group by tag_id and keep only the most recent position for each tag
      const latestByTag = new Map();
      data.forEach((pos: Position) => {
        const existing = latestByTag.get(pos.tag_id);
        if (!existing || new Date(pos.timestamp) > new Date(existing.timestamp)) {
          latestByTag.set(pos.tag_id, pos);
        }
      });
      
      setPositions(Array.from(latestByTag.values()));
      setConnected(data.length > 0);
    } catch (error) {
      console.error('Error fetching positions:', error);
      setConnected(false);
    }
  };

  // Fetch items detected near employee (within 1.5m range)
  const fetchItems = async () => {
    try {
      // Use new endpoint that returns unique items by product_id
      // This prevents items from disappearing when query limit is exceeded
      const response = await fetch('http://localhost:8000/data/items');
      const data = await response.json();
      
      // Filter to only show items with 'present' status (not missing)
      const presentItems = data.filter((item: any) => 
        item.x_position && 
        item.y_position && 
        item.status === 'present'
      );
      
      setItems(presentItems.map((item: any) => ({
        product_id: item.product_id,
        product_name: item.product_name,
        x_position: item.x_position,
        y_position: item.y_position,
        status: item.status,
        timestamp: item.timestamp,
      })));
    } catch (error) {
      console.error('Error fetching items:', error);
    }
  };

  // Fetch missing items separately (always shown)
  const fetchMissingItems = async () => {
    try {
      const response = await fetch('http://localhost:8000/data/missing');
      const data = await response.json();
      
      setMissingItems(data.map((item: any) => ({
        product_id: item.product_id,
        product_name: item.product_name,
        x_position: item.x_position,
        y_position: item.y_position,
        status: item.status,
        timestamp: item.timestamp,
      })));
    } catch (error) {
      console.error('Error fetching missing items:', error);
    }
  };  // Initial load
  useEffect(() => {
    const init = async () => {
      await fetchAnchors();
      await fetchPositions();
      await fetchItems();
      await fetchMissingItems();
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
      fetchMissingItems();
    }, 200); // Refresh every 200ms (5x per second) for smooth tracking
    
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

  // Clear all tracking data (positions and items)
  const handleClearData = async () => {
    if (!confirm('Clear all tracking data? This will remove all positions and item history from the database.')) return;

    try {
      // Call backend to clear database
      const response = await fetch(`${API_URL}/data/clear`, { method: 'DELETE' });
      
      if (response.ok) {
        const result = await response.json();
        console.log('Data cleared:', result);
        
        // Clear positions and items from display
        setPositions([]);
        setItems([]);
        
        alert(`Cleared: ${result.positions_deleted} positions, ${result.detections_deleted} detections, ${result.uwb_measurements_deleted} measurements`);
      } else {
        throw new Error('Failed to clear data');
      }
    } catch (error) {
      console.error('Failed to clear data:', error);
      alert('Failed to clear data. Check console for details.');
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
    <div className="min-h-screen p-8 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <header className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-5xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-emerald-400 text-transparent bg-clip-text">
              🏪 OptiFlow
            </h1>
            <p className="text-slate-400 text-lg">Real-time Store Inventory & Employee Tracking</p>
          </div>
          
          <div className="flex flex-col items-end gap-2">
            <div className={`px-4 py-2 rounded-lg flex items-center gap-2 ${connected ? 'bg-green-900/30 border-2 border-green-700' : 'bg-red-900/30 border-2 border-red-700'}`}>
              <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`}></div>
              <span className="mr-2 text-slate-300">System:</span>
              <span className={`font-bold ${connected ? 'text-green-400' : 'text-red-400'}`}>
                {connected ? 'LIVE' : 'OFFLINE'}
              </span>
            </div>
            {missingItems.length > 0 && (
              <div className="px-4 py-2 rounded-lg bg-red-900/40 border-2 border-red-500 animate-pulse">
                <span className="font-bold text-red-300">
                  ⚠️ {missingItems.length} Items Need Restocking
                </span>
              </div>
            )}
          </div>
        </div>
        
        <div className="mt-6 grid grid-cols-4 gap-4">
          <div className="bg-slate-800/70 backdrop-blur-sm p-4 rounded-lg border border-slate-700">
            <div className="flex items-center gap-3">
              <div className="text-3xl">📡</div>
              <div>
                <p className="text-slate-400 text-sm">UWB Anchors</p>
                <p className="text-2xl font-bold text-blue-400">
                  {anchors.filter(a => a.is_active).length}/{anchors.length}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-slate-800/70 backdrop-blur-sm p-4 rounded-lg border border-slate-700">
            <div className="flex items-center gap-3">
              <div className="text-3xl">🚶</div>
              <div>
                <p className="text-slate-400 text-sm">Employees</p>
                <p className="text-2xl font-bold text-emerald-400">
                  {new Set(positions.map(p => p.tag_id)).size}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-slate-800/70 backdrop-blur-sm p-4 rounded-lg border border-slate-700">
            <div className="flex items-center gap-3">
              <div className="text-3xl">📦</div>
              <div>
                <p className="text-slate-400 text-sm">Items Tracked</p>
                <p className="text-2xl font-bold text-white">
                  {items.length + missingItems.length}
                </p>
              </div>
            </div>
          </div>
          
          <div className={`p-4 rounded-lg border-2 ${
            missingItems.length > 0 
              ? 'bg-red-900/40 border-red-500' 
              : 'bg-slate-800/70 border-slate-700'
          }`}>
            <div className="flex items-center gap-3">
              <div className="text-3xl">⚠️</div>
              <div>
                <p className="text-slate-400 text-sm">Missing Items</p>
                <p className={`text-2xl font-bold ${
                  missingItems.length > 0 
                    ? 'text-red-400' 
                    : 'text-slate-400'
                }`}>
                  {missingItems.length}
                </p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="mb-6 flex flex-wrap gap-4 items-center">
        <button
          onClick={() => setSetupMode(!setupMode)}
          className={`px-6 py-3 rounded-lg font-semibold transition-colors ${
            setupMode 
              ? 'bg-green-600 hover:bg-green-700 text-white' 
              : 'bg-blue-600 hover:bg-blue-700 text-white'
          }`}
        >
          {setupMode ? '✓ Finish Setup' : '⚙️ Setup Mode'}
        </button>
        
        {setupMode && (
          <>
            <button
              onClick={handleResetAnchors}
              className="px-6 py-3 rounded-lg font-semibold bg-red-700 hover:bg-red-600 text-white transition-colors"
            >
              🗑️ Reset Anchors
            </button>
            
            <div className="ml-auto text-sm text-slate-400 flex items-center">
              <div className="bg-slate-800 px-4 py-2 rounded-lg border border-slate-700">
                💡 Click on the map to place anchors. Drag to reposition.
              </div>
            </div>
          </>
        )}
        
        {!setupMode && (
          <>
            <button
              onClick={fetchPositions}
              className="px-6 py-3 rounded-lg font-semibold bg-slate-700 hover:bg-slate-600 text-white transition-colors"
            >
              🔄 Refresh
            </button>
            
            <button
              onClick={handleClearData}
              className="px-6 py-3 rounded-lg font-semibold bg-yellow-700 hover:bg-yellow-600 text-white transition-colors"
            >
              🧹 Clear Data
            </button>
            
            {positions.length === 0 && anchors.length >= 2 && (
              <div className="ml-auto text-sm flex items-center">
                <div className="bg-blue-900/30 border border-blue-700 px-4 py-2 rounded-lg text-blue-300">
                  📡 Ready! Run: <code className="bg-slate-800 px-2 py-1 rounded ml-2">python3 esp32_simulator.py</code>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div className="xl:col-span-2">
          <div className="bg-slate-800/70 backdrop-blur-sm p-6 rounded-lg border border-slate-700 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-semibold">📍 Live Store Map</h2>
              <div className="text-sm text-slate-400">
                {!setupMode && positions.length > 0 && (
                  <span className="bg-green-900/30 text-green-400 px-3 py-1 rounded-full border border-green-700">
                    ● Tracking Active
                  </span>
                )}
              </div>
            </div>
            <StoreMap
              anchors={anchors}
              positions={positions}
              items={[...items, ...missingItems]}
              setupMode={setupMode}
              onAnchorPlace={handleAnchorPlace}
              onAnchorUpdate={handleAnchorUpdate}
            />
          </div>
        </div>

        <div className="space-y-6">
          {/* Missing Items - Items Needing Restock */}
          <div className={`p-6 rounded-lg border-2 ${
            missingItems.length > 0 
              ? 'bg-red-900/40 border-red-500' 
              : 'bg-slate-800/70 border-slate-700'
          }`}>
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <span className="text-2xl">📋</span>
              <span className={missingItems.length > 0 ? 'text-red-300' : 'text-slate-300'}>
                Restock Queue ({missingItems.length})
              </span>
            </h2>
            
            {missingItems.length === 0 ? (
              <div className="text-center py-8">
                <div className="text-5xl mb-3">✅</div>
                <p className="text-slate-400">All items accounted for!</p>
                <p className="text-slate-500 text-sm mt-2">No restocking needed</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[500px] overflow-y-auto">
                {missingItems.map((item, index) => (
                  <div
                    key={item.product_id}
                    className="p-3 bg-slate-800 rounded border border-red-500/40 hover:bg-slate-750 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-red-400 font-bold">#{index + 1}</span>
                          <span className="font-semibold text-red-300">{item.product_name}</span>
                        </div>
                        <div className="text-xs text-slate-400 space-y-0.5">
                          <div className="font-mono">ID: {item.product_id}</div>
                          <div>Location: ({Math.round(item.x_position)}cm, {Math.round(item.y_position)}cm)</div>
                          {item.timestamp && (
                            <div>Last seen: {new Date(item.timestamp).toLocaleTimeString()}</div>
                          )}
                        </div>
                      </div>
                      <div className="text-2xl">⚠️</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {missingItems.length > 0 && (
              <div className="mt-4 pt-4 border-t border-red-500/30">
                <div className="text-sm text-red-300 flex items-center justify-between">
                  <span>Priority: High</span>
                  <span className="font-bold">{missingItems.length} items to restock</span>
                </div>
              </div>
            )}
          </div>

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

          {/* Quick Start Guide */}
          {anchors.length === 0 && (
            <div className="bg-blue-900/30 border-2 border-blue-500 p-6 rounded-lg">
              <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <span className="text-2xl">🚀</span>
                Setup Guide
              </h3>
              <div className="space-y-4">
                <div className="bg-slate-800/50 p-4 rounded-lg border border-blue-700/50">
                  <h4 className="font-semibold text-blue-300 mb-2">Step 1: Configure Anchors</h4>
                  <ol className="text-sm space-y-2 text-slate-300 ml-4">
                    <li>1. Click "⚙️ Setup Mode" button above</li>
                    <li>2. Place anchors on the map by clicking at their physical locations</li>
                    <li>3. Drag anchors to adjust positions if needed</li>
                    <li>4. Place at least 2 anchors (4 recommended for best accuracy)</li>
                    <li>5. Click "✓ Finish Setup" when done</li>
                  </ol>
                </div>
                
                <div className="bg-slate-800/50 p-4 rounded-lg border border-blue-700/50">
                  <h4 className="font-semibold text-blue-300 mb-2">Step 2: Start Simulator</h4>
                  <p className="text-sm text-slate-300 mb-2">Run the ESP32 simulator (will auto-load anchor config):</p>
                  <code className="block bg-slate-900 px-3 py-2 rounded text-xs text-green-400 font-mono">
                    python3 esp32_simulator.py
                  </code>
                </div>
                
                <div className="bg-yellow-900/30 border border-yellow-700/50 p-4 rounded-lg">
                  <p className="text-xs text-yellow-200 flex items-start gap-2">
                    <span className="text-lg">💡</span>
                    <span>
                      <strong>Tip:</strong> Employee movement follows store aisles, not anchor positions. 
                      Place anchors at the corners or edges of your store for best triangulation accuracy.
                    </span>
                  </p>
                </div>
              </div>
            </div>
          )}
          
          {/* Anchor Configuration Status */}
          {anchors.length > 0 && anchors.length < 2 && (
            <div className="bg-yellow-900/30 border-2 border-yellow-500 p-6 rounded-lg">
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2 text-yellow-300">
                <span>⚠️</span>
                Insufficient Anchors
              </h3>
              <p className="text-sm text-yellow-200 mb-3">
                You have {anchors.length} anchor(s) configured. At least 2 active anchors are required for position tracking.
              </p>
              <button
                onClick={() => setSetupMode(true)}
                className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg font-semibold transition-colors"
              >
                Add More Anchors
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
