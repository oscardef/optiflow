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

interface Item {
  product_id: string;
  product_name: string;
  x_position: number;
  y_position: number;
  status: string;
  timestamp?: string;
}

type ViewMode = 'live' | 'stock-heatmap';

export default function Home() {
  const [viewMode, setViewMode] = useState<ViewMode>('live');
  const [setupMode, setSetupMode] = useState(false);
  const [anchors, setAnchors] = useState<Anchor[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [missingItems, setMissingItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const [activePanel, setActivePanel] = useState<'missing' | 'anchors' | 'positions' | null>('missing');
  const [expandedRestockItems, setExpandedRestockItems] = useState<Set<string>>(new Set());
  const [products, setProducts] = useState<any[]>([]);
  const [stockHeatmap, setStockHeatmap] = useState<any[]>([]);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [highlightedItem, setHighlightedItem] = useState<string | null>(null);
  const [currentMode, setCurrentMode] = useState<'SIMULATION' | 'REAL'>('SIMULATION');
  const [simulationRunning, setSimulationRunning] = useState(false);

  const fetchAnchors = async () => {
    try {
      const response = await fetch(`${API_URL}/anchors`);
      const data = await response.json();
      setAnchors(data);
    } catch (error) {
      console.error('Error fetching anchors:', error);
    }
  };

  const fetchPositions = async () => {
    try {
      const response = await fetch(`${API_URL}/positions/latest?limit=100`);
      const data = await response.json();
      
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

  const fetchItems = async () => {
    try {
      const response = await fetch(`${API_URL}/data/items`);
      const data = await response.json();
      
      const presentItems = data.filter((item: any) => 
        item.x_position && 
        item.y_position && 
        item.status === 'present'
      );
      
      setItems(presentItems);
    } catch (error) {
      console.error('Error fetching items:', error);
    }
  };

  const fetchMissingItems = async () => {
    try {
      const response = await fetch(`${API_URL}/data/missing`);
      const data = await response.json();
      setMissingItems(data);
    } catch (error) {
      console.error('Error fetching missing items:', error);
    }
  };

  const fetchProducts = async () => {
    try {
      const response = await fetch(`${API_URL}/products`);
      const data = await response.json();
      setProducts(data);
    } catch (error) {
      console.error('Error fetching products:', error);
    }
  };

  const fetchStockHeatmap = async () => {
    try {
      const response = await fetch(`${API_URL}/analytics/stock-heatmap`);
      const data = await response.json();
      setStockHeatmap(data);
    } catch (error) {
      console.error('Error fetching stock heatmap:', error);
    }
  };

  const fetchMode = async () => {
    try {
      const response = await fetch(`${API_URL}/config/mode`);
      const data = await response.json();
      setCurrentMode(data.mode);
      setSimulationRunning(data.simulation_running);
    } catch (error) {
      console.error('Error fetching mode:', error);
    }
  };

  const startSimulation = async () => {
    try {
      const response = await fetch(`${API_URL}/simulation/start`, { method: 'POST' });
      const data = await response.json();
      if (data.success) {
        alert('Simulation started successfully');
        await fetchMode();
      } else {
        alert(data.message || 'Failed to start simulation');
      }
    } catch (error) {
      alert('Failed to start simulation');
    }
  };

  const stopSimulation = async () => {
    try {
      const response = await fetch(`${API_URL}/simulation/stop`, { method: 'POST' });
      const data = await response.json();
      if (data.success) {
        alert('Simulation stopped successfully');
        await fetchMode();
      } else {
        alert(data.message || 'Failed to stop simulation');
      }
    } catch (error) {
      alert('Failed to stop simulation');
    }
  };



  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    if (query.trim().length < 2) {
      setSearchResults([]);
      setHighlightedItem(null);
      return;
    }

    try {
      const response = await fetch(`${API_URL}/search/items?q=${encodeURIComponent(query)}`);
      const data = await response.json();
      setSearchResults(data.items || []);
    } catch (error) {
      console.error('Error searching items:', error);
      setSearchResults([]);
    }
  };

  const handleItemClick = async (rfidTag: string) => {
    try {
      const response = await fetch(`${API_URL}/items/${rfidTag}`);
      const data = await response.json();
      setSelectedItem(data);
      setHighlightedItem(rfidTag);
      setActivePanel(null); // Show item detail
    } catch (error) {
      console.error('Error fetching item details:', error);
    }
  };

  useEffect(() => {
    const init = async () => {
      await fetchAnchors();
      await fetchPositions();
      await fetchItems();
      await fetchMissingItems();
      await fetchProducts();
      await fetchMode();
      setLoading(false);
    };
    init();
  }, []);

  useEffect(() => {
    if (setupMode) return;
    
    const interval = setInterval(() => {
      fetchPositions();
      fetchItems();
      fetchMissingItems();
      fetchMode();
      
      if (viewMode !== 'live') {
        fetchProducts();
        if (viewMode === 'stock-heatmap') fetchStockHeatmap();
      }
    }, 200);
    
    return () => clearInterval(interval);
  }, [setupMode, viewMode]);

  useEffect(() => {
    if (viewMode === 'stock-heatmap') fetchStockHeatmap();
  }, [viewMode]);

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
      }
    } catch (error) {
      console.error('Failed to create anchor:', error);
    }
  };

  const handleAnchorUpdate = async (anchorId: number, x: number, y: number) => {
    try {
      await fetch(`${API_URL}/anchors/${anchorId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          x_position: Math.round(x),
          y_position: Math.round(y)
        })
      });
      await fetchAnchors();
    } catch (error) {
      console.error('Failed to update anchor:', error);
    }
  };

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

  const handleClearData = async () => {
    if (!confirm('Clear all tracking data?')) return;

    try {
      await fetch(`${API_URL}/data/clear`, { method: 'DELETE' });
      
      // Clear all state
      setPositions([]);
      setItems([]);
      setMissingItems([]);
      setStockHeatmap([]);
      
      // Force immediate refetch from backend to ensure cleared state
      await Promise.all([
        fetchItems(),
        fetchMissingItems(),
        viewMode === 'stock-heatmap' ? fetchStockHeatmap() : Promise.resolve()
      ]);
    } catch (error) {
      console.error('Failed to clear data:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="text-xl text-gray-600">Loading...</div>
      </div>
    );
  }

  const stats = [
    { label: 'Anchors', value: `${anchors.filter(a => a.is_active).length}/${anchors.length}`, status: anchors.filter(a => a.is_active).length >= 2 ? 'good' : 'warning' },
    { label: 'Employees', value: new Set(positions.map(p => p.tag_id)).size, status: 'good' },
    { label: 'Items', value: items.length + missingItems.length, status: 'good' },
    { label: 'Missing', value: missingItems.length, status: missingItems.length > 0 ? 'alert' : 'good' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">OptiFlow</h1>
              <p className="text-sm text-gray-600 mt-0.5">Real-time Store Tracking System</p>
            </div>
            
            <div className="flex items-center gap-4">
              {!setupMode && (
                <>
                  <a
                    href="/admin"
                    className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-[#0055A4] hover:bg-gray-50 border border-gray-300 rounded transition-colors"
                  >
                    Admin Panel
                  </a>
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="Search items..."
                      value={searchQuery}
                      onChange={(e) => handleSearch(e.target.value)}
                      className="px-4 py-2 border border-gray-300 focus:outline-none focus:border-[#0055A4] w-64 text-sm"
                    />
                    {searchResults.length > 0 && (
                    <div className="absolute top-full mt-1 w-full bg-white border border-gray-200 shadow-lg max-h-96 overflow-y-auto z-50">
                      {searchResults.map((result) => (
                        <button
                          key={result.rfid_tag}
                          onClick={() => {
                            handleItemClick(result.rfid_tag);
                            setSearchQuery('');
                            setSearchResults([]);
                          }}
                          className="w-full px-4 py-2 text-left hover:bg-gray-50 border-b border-gray-100 text-sm"
                        >
                          <div className="font-medium text-gray-900">{result.name}</div>
                          <div className="text-xs text-gray-500">{result.rfid_tag} • {result.status}</div>
                        </button>
                      ))}
                    </div>
                    )}
                  </div>
                </>
              )}
              
              <div className={`flex items-center gap-2 px-3 py-1.5 border ${
                connected 
                  ? 'border-green-200 bg-green-50' 
                  : 'border-red-200 bg-red-50'
              }`}>
                <div className={`w-2 h-2 rounded-full ${
                  connected ? 'bg-green-500' : 'bg-red-500'
                }`}></div>
                <span className={`text-sm font-medium ${
                  connected ? 'text-green-700' : 'text-red-700'
                }`}>
                  {connected ? 'LIVE' : 'OFFLINE'}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 mt-3">
            <button
              onClick={() => setSetupMode(!setupMode)}
              className={setupMode ? 'btn-primary bg-green-600 hover:bg-green-700' : 'btn-primary'}
            >
              {setupMode ? 'Finish Setup' : 'Setup Mode'}
            </button>
            
            {setupMode && (
              <button onClick={handleResetAnchors} className="btn-secondary text-red-600 border-red-200 hover:bg-red-50">
                Reset Anchors
              </button>
            )}
            
            {!setupMode && (
              <>
                <button onClick={handleClearData} className="btn-secondary">
                  Clear Data
                </button>
                {currentMode === 'SIMULATION' && (
                  simulationRunning ? (
                    <button 
                      onClick={stopSimulation}
                      className="btn-primary bg-red-600 hover:bg-red-700"
                    >
                      Stop Simulation
                    </button>
                  ) : (
                    <button 
                      onClick={startSimulation}
                      className="btn-primary bg-purple-600 hover:bg-purple-700"
                    >
                      Start Simulation
                    </button>
                  )
                )}
              </>
            )}

            <div className="ml-auto">
              <button
                onClick={() => setShowSidebar(!showSidebar)}
                className="btn-secondary"
              >
                {showSidebar ? 'Hide' : 'Show'} Panels
              </button>
            </div>
          </div>


        </div>
      </header>

      <div className="flex h-[calc(100vh-160px)] overflow-hidden">
        {!setupMode && (
          <div className="flex flex-col gap-2 p-2 bg-white border-r border-gray-200">
            <button
              onClick={() => setViewMode('live')}
              className={`p-3 transition-colors border-2 ${
                viewMode === 'live'
                  ? 'bg-[#0055A4] text-white border-[#0055A4]'
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }`}
              title="Live Tracking"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
            <button
              onClick={() => setViewMode('stock-heatmap')}
              className={`p-3 transition-colors border-2 ${
                viewMode === 'stock-heatmap'
                  ? 'bg-[#0055A4] text-white border-[#0055A4]'
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }`}
              title="Stock Heatmap"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </button>
          </div>
        )}
        <div className="flex-1 p-4 min-h-0">
          <div className="h-full flex flex-col">
            <div className="flex-1 min-h-0">
              <StoreMap
                anchors={anchors}
                positions={positions}
                items={[...items, ...missingItems]}
                setupMode={setupMode}
                viewMode={viewMode}
                stockHeatmap={stockHeatmap}
                highlightedItem={highlightedItem}
                onAnchorPlace={handleAnchorPlace}
                onAnchorUpdate={handleAnchorUpdate}
                onItemClick={(item) => handleItemClick(item.product_id)}
              />
            </div>
          </div>
        </div>

        {showSidebar && (
          <div className="w-[30vw] bg-white border-l border-gray-200 flex flex-col">
            {/* Stats Grid - 2x2 */}
            <div className="grid grid-cols-2 gap-2 p-3 border-b border-gray-200">
              {stats.map((stat) => (
                <div key={stat.label} className="border border-gray-200 bg-white px-2 py-2">
                  <div className="text-[10px] text-gray-500 uppercase tracking-wide mb-0.5">
                    {stat.label}
                  </div>
                  <div className={`text-lg font-bold ${
                    stat.status === 'alert' ? 'text-red-600' :
                    stat.status === 'warning' ? 'text-yellow-600' :
                    'text-gray-900'
                  }`}>
                    {stat.value}
                  </div>
                </div>
              ))}
            </div>
            
            <div className="flex border-b border-gray-200">
              {[
                { id: 'missing', label: 'Restock', count: missingItems.length },
                { id: 'anchors', label: 'Anchors', count: anchors.length },
                { id: 'positions', label: 'Positions', count: positions.length },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActivePanel(activePanel === tab.id as any ? null : tab.id as any)}
                  className={`flex-1 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                    activePanel === tab.id
                      ? 'border-[#0055A4] text-[#0055A4]'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {tab.label}
                  {tab.count > 0 && (
                    <span className={`ml-2 px-2 py-0.5 text-xs font-semibold ${
                      tab.id === 'missing' && tab.count > 0
                        ? 'bg-red-100 text-red-700'
                        : 'bg-gray-100 text-gray-700'
                    }`}>
                      {tab.count}
                    </span>
                  )}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto">
              {activePanel === 'missing' && (
                <div className="p-4">
                  {missingItems.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                      <div className="text-4xl mb-2">✓</div>
                      <p className="text-sm">All items in stock</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {missingItems.map((item, index) => {
                        const isExpanded = expandedRestockItems.has(item.product_id);
                        return (
                          <div
                            key={item.product_id}
                            className="border-l-4 border-red-500 bg-white hover:bg-gray-50 transition-colors"
                          >
                            <div
                              className="p-3 cursor-pointer"
                              onClick={async () => {
                                await handleItemClick(item.product_id);
                              }}
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3 flex-1">
                                  <span className="text-xs font-bold text-red-600 bg-red-100 px-2 py-1 rounded">HIGH</span>
                                  <span className="text-sm font-semibold text-gray-900">
                                    {item.product_name}
                                  </span>
                                </div>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setExpandedRestockItems(prev => {
                                      const next = new Set(prev);
                                      if (next.has(item.product_id)) {
                                        next.delete(item.product_id);
                                      } else {
                                        next.add(item.product_id);
                                      }
                                      return next;
                                    });
                                  }}
                                  className="text-gray-400 hover:text-gray-600 p-1"
                                >
                                  <svg className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                  </svg>
                                </button>
                              </div>
                            </div>
                            {isExpanded && (
                              <div className="px-3 pb-3 pt-0 border-t border-gray-100 bg-gray-50">
                                <div className="text-xs text-gray-600 space-y-1 mt-2">
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">RFID Tag:</span>
                                    <span className="font-mono">{item.product_id}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-gray-500">Last Location:</span>
                                    <span>({Math.round(item.x_position)}, {Math.round(item.y_position)}) cm</span>
                                  </div>
                                  {item.timestamp && (
                                    <div className="flex justify-between">
                                      <span className="text-gray-500">Last Seen:</span>
                                      <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {selectedItem && activePanel !== 'missing' && (
                <div className="p-4 border-b border-gray-200 bg-white">
                  <div className="flex items-start justify-between mb-4">
                    <h3 className="text-xl font-bold text-gray-900">{selectedItem.name}</h3>
                    <button
                      onClick={() => {
                        setSelectedItem(null);
                        setHighlightedItem(null);
                      }}
                      className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
                    >
                      ×
                    </button>
                  </div>
                  
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="border-2 border-gray-200 bg-white p-4 rounded-lg">
                        <div className="text-xs text-gray-500 uppercase font-semibold mb-1">Currently In Stock</div>
                        <div className="text-2xl font-bold text-green-600">
                          {selectedItem.inventory_summary?.in_stock || 0}
                        </div>
                      </div>
                      
                      <div className="border-2 border-gray-200 bg-white p-4 rounded-lg">
                        <div className="text-xs text-gray-500 uppercase font-semibold mb-1">Max Detected</div>
                        <div className="text-2xl font-bold text-gray-900">
                          {selectedItem.inventory_summary?.max_detected || 0}
                        </div>
                      </div>
                    </div>
                    
                    {selectedItem.inventory_summary?.missing > 0 && (
                      <div className="bg-red-50 border-2 border-red-200 p-4 rounded-lg">
                        <div className="text-center">
                          <div className="text-3xl font-bold text-red-600 mb-1">
                            {selectedItem.inventory_summary.missing}
                          </div>
                          <div className="text-xs text-red-700 font-semibold uppercase">
                            Items Need Restocking
                          </div>
                        </div>
                      </div>
                    )}
                    
                    <div className="border border-gray-200 bg-gray-50 p-4 rounded-lg">
                      <div className="text-xs text-gray-500 uppercase font-semibold mb-2">Last Known Location</div>
                      <div className="text-sm text-gray-900 space-y-1">
                        <div className="flex justify-between">
                          <span className="text-gray-500">X:</span>
                          <span className="font-mono">{Math.round(selectedItem.x_position)} cm</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Y:</span>
                          <span className="font-mono">{Math.round(selectedItem.y_position)} cm</span>
                        </div>
                      </div>
                    </div>
                    
                    {selectedItem.last_seen && (
                      <div className="border border-gray-200 bg-gray-50 p-4 rounded-lg">
                        <div className="text-xs text-gray-500 uppercase font-semibold mb-2">Last Seen</div>
                        <div className="text-sm text-gray-900">
                          {new Date(selectedItem.last_seen).toLocaleString()}
                        </div>
                      </div>
                    )}
                    
                    <div className="pt-2">
                      <div className="text-xs text-gray-400 font-mono text-center">
                        {selectedItem.rfid_tag}
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              {activePanel === 'anchors' && (
                <div className="p-4">
                  {anchors.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                      <p className="text-sm">No anchors configured</p>
                      <p className="text-xs mt-2">Enable Setup Mode to add anchors</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {anchors.map((anchor) => (
                        <div key={anchor.id} className="border border-gray-200 bg-white p-3">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-semibold text-sm text-gray-900">
                              {anchor.name}
                            </span>
                            <span className={`text-xs px-2 py-0.5 font-medium ${
                              anchor.is_active
                                ? 'bg-green-100 text-green-700'
                                : 'bg-gray-100 text-gray-700'
                            }`}>
                              {anchor.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </div>
                          <div className="text-xs text-gray-600 space-y-0.5">
                            <div className="font-mono">{anchor.mac_address}</div>
                            <div>
                              Position: ({Math.round(anchor.x_position)}, {Math.round(anchor.y_position)}) cm
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activePanel === 'positions' && (
                <div className="p-4">
                  {positions.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                      <p className="text-sm">No position data</p>
                      <p className="text-xs mt-2">Start the simulator or connect hardware</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {positions.slice(0, 10).map((pos) => (
                        <div key={pos.id} className="border border-gray-200 bg-white p-3">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-semibold text-sm text-gray-900">
                              {pos.tag_id}
                            </span>
                            <span className="text-xs text-gray-500">
                              {new Date(pos.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                          <div className="text-xs text-gray-600 space-y-1">
                            <div>
                              Position: ({Math.round(pos.x_position)}, {Math.round(pos.y_position)}) cm
                            </div>
                            <div className="flex items-center justify-between">
                              <span>Confidence: {(pos.confidence * 100).toFixed(0)}%</span>
                              <span>{pos.num_anchors} anchors</span>
                            </div>
                            <div className="w-full bg-gray-200 h-1 mt-1">
                              <div
                                className="bg-[#0055A4] h-1 transition-all"
                                style={{ width: `${pos.confidence * 100}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Floating Product Info Panel - appears when clicking restock item */}
        {selectedItem && activePanel === 'missing' && (
          <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-2xl w-full max-w-md max-h-[80vh] overflow-y-auto">
              <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-start justify-between">
                <h3 className="text-xl font-bold text-gray-900">{selectedItem.name}</h3>
                <button
                  onClick={() => {
                    setSelectedItem(null);
                    setHighlightedItem(null);
                    setActivePanel('missing');
                  }}
                  className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
                >
                  ×
                </button>
              </div>
              
              <div className="p-6 space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="border-2 border-gray-200 bg-white p-4 rounded-lg">
                    <div className="text-xs text-gray-500 uppercase font-semibold mb-1">Currently In Stock</div>
                    <div className="text-2xl font-bold text-green-600">
                      {selectedItem.inventory_summary?.in_stock || 0}
                    </div>
                  </div>
                  
                  <div className="border-2 border-gray-200 bg-white p-4 rounded-lg">
                    <div className="text-xs text-gray-500 uppercase font-semibold mb-1">Max Detected</div>
                    <div className="text-2xl font-bold text-gray-900">
                      {selectedItem.inventory_summary?.max_detected || 0}
                    </div>
                  </div>
                </div>
                
                {selectedItem.inventory_summary?.missing > 0 && (
                  <div className="bg-red-50 border-2 border-red-200 p-4 rounded-lg">
                    <div className="text-center">
                      <div className="text-3xl font-bold text-red-600 mb-1">
                        {selectedItem.inventory_summary.missing}
                      </div>
                      <div className="text-xs text-red-700 font-semibold uppercase">
                        Items Need Restocking
                      </div>
                    </div>
                  </div>
                )}
                
                <div className="border border-gray-200 bg-gray-50 p-4 rounded-lg">
                  <div className="text-xs text-gray-500 uppercase font-semibold mb-2">Last Known Location</div>
                  <div className="text-sm text-gray-900 space-y-1">
                    <div className="flex justify-between">
                      <span className="text-gray-500">X:</span>
                      <span className="font-mono">{Math.round(selectedItem.x_position)} cm</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Y:</span>
                      <span className="font-mono">{Math.round(selectedItem.y_position)} cm</span>
                    </div>
                  </div>
                </div>
                
                {selectedItem.last_seen && (
                  <div className="border border-gray-200 bg-gray-50 p-4 rounded-lg">
                    <div className="text-xs text-gray-500 uppercase font-semibold mb-2">Last Seen</div>
                    <div className="text-sm text-gray-900">
                      {new Date(selectedItem.last_seen).toLocaleString()}
                    </div>
                  </div>
                )}
                
                <div className="pt-2">
                  <div className="text-xs text-gray-400 font-mono text-center">
                    {selectedItem.rfid_tag}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
