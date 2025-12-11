'use client';

import { useState, useEffect, useCallback } from 'react';
import StoreMap from './components/StoreMap';
import { useWebSocket } from './hooks/useWebSocket';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

// Debug: Log environment variables at module load time
console.log('[MODULE LOAD] Environment variables:', {
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL,
  API_URL,
  WS_URL,
});

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
  const [showSidebar, setShowSidebar] = useState(true);
  const [activePanel, setActivePanel] = useState<'missing' | 'anchors' | 'positions' | null>('missing');
  const [expandedRestockItems, setExpandedRestockItems] = useState<Set<string>>(new Set());
  const [products, setProducts] = useState<any[]>([]);
  const [stockHeatmap, setStockHeatmap] = useState<any[]>([]);
  const [maxDisplayItems, setMaxDisplayItems] = useState<number>(500);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [highlightedItem, setHighlightedItem] = useState<string | null>(null);
  const [currentMode, setCurrentMode] = useState<'SIMULATION' | 'PRODUCTION'>('SIMULATION');
  const [simulationRunning, setSimulationRunning] = useState(false);
  
  // Anchor placement modal state for PRODUCTION mode
  const [pendingAnchor, setPendingAnchor] = useState<{x: number, y: number, index: number} | null>(null);
  const [anchorMacInput, setAnchorMacInput] = useState('');
  const [anchorNameInput, setAnchorNameInput] = useState('');
  
  // Clear data confirmation modal
  const [showClearDataModal, setShowClearDataModal] = useState(false);
  
  // WebSocket connection state
  const [wsConnected, setWsConnected] = useState(false);
  const [lastMessageTime, setLastMessageTime] = useState<number | null>(null);
  const [receivingData, setReceivingData] = useState(false);
  
  // Hardware control state (for PRODUCTION mode)
  const [hardwareActive, setHardwareActive] = useState(false);

  // WebSocket message handler
  const handleWebSocketMessage = useCallback((message: any) => {
    console.log('[DEBUG] Processing WebSocket message:', message.type, message.data);
    
    // Track last message time for "receiving data" indicator
    setLastMessageTime(Date.now());
    setReceivingData(true);
    
    switch (message.type) {
      case 'position_update':
        if (message.data) {
          console.log('[DEBUG] Adding position:', message.data);
          setPositions(prev => {
            // Create new position object with correct property names
            const newPosition = {
              id: Date.now(),
              tag_id: message.data.tag_id,
              x_position: message.data.x,
              y_position: message.data.y,
              confidence: message.data.confidence,
              timestamp: message.data.timestamp,
              num_anchors: message.data.num_anchors
            };
            // Deduplicate by tag_id - keep only the latest position for each tag
            const latestByTag = new Map();
            
            // Add the new position first
            latestByTag.set(newPosition.tag_id, newPosition);
            
            // Then add existing positions, but only if we don't already have a newer one for that tag
            prev.forEach(pos => {
              if (!latestByTag.has(pos.tag_id)) {
                latestByTag.set(pos.tag_id, pos);
              }
            });
            
            const newPositions = Array.from(latestByTag.values());
            console.log('[DEBUG] Updated positions array, length:', newPositions.length, 'unique tags:', newPositions.map(p => p.tag_id));
            return newPositions;
          });
        }
        break;
      
      case 'item_update':
        if (message.data && message.data.items) {
          console.log('[DEBUG] Updating items, count:', message.data.count);
          setItems(prev => {
            // Create a map of existing items by rfid_tag
            const itemMap = new Map(prev.map(item => [item.product_id || item.rfid_tag, item]));
            
            // Update or add new items
            message.data.items.forEach((newItem: any) => {
              const key = newItem.product_id || newItem.rfid_tag;
              itemMap.set(key, {
                product_id: newItem.rfid_tag,
                product_name: newItem.product_name,
                x_position: newItem.x,
                y_position: newItem.y,
                status: newItem.status,
                timestamp: new Date().toISOString()
              });
            });
            
            return Array.from(itemMap.values());
          });
        }
        break;
      
      case 'detection_update':
        // Could be used for real-time detection notifications
        console.log('Detection update:', message.data);
        break;
      
      case 'missing_update':
        if (message.data && message.data.missing_items) {
          console.log('[DEBUG] Updating missing items, count:', message.data.count);
          setMissingItems(message.data.missing_items.map((item: any) => ({
            product_id: item.rfid_tag,
            product_name: item.product_name,
            x_position: item.x,
            y_position: item.y,
            status: item.status
          })));
        }
        break;
      
      default:
        console.log('Unknown WebSocket message type:', message.type);
    }
  }, [maxDisplayItems]);

  // Initialize WebSocket connection
  useWebSocket({
    url: WS_URL,
    enabled: !setupMode, // Only connect when not in setup mode
    onMessage: handleWebSocketMessage,
    onConnect: () => {
      console.log('WebSocket connected successfully');
      setWsConnected(true);
    },
    onDisconnect: () => {
      console.log('WebSocket disconnected');
      setWsConnected(false);
      setReceivingData(false);
    },
    onError: (error) => {
      console.warn('WebSocket connection issue (will retry)', {
        wsUrl: WS_URL,
        type: error.type,
        message: 'Check that the backend is running and accessible'
      });
      setWsConnected(false);
      setReceivingData(false);
    },
  });

  // Monitor WebSocket data reception - if no messages for 5 seconds, mark as not receiving
  useEffect(() => {
    const interval = setInterval(() => {
      if (lastMessageTime && Date.now() - lastMessageTime > 2000) {
        setReceivingData(false);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [lastMessageTime]);

  const fetchAnchors = async () => {
    try {
      const response = await fetch(`${API_URL}/anchors`);
      if (!response.ok) {
        throw new Error(`Failed to fetch anchors: ${response.status} ${response.statusText}`);
      }
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
      
      console.log('[DEBUG] Fetched positions:', data.length, 'raw positions');
      
      const latestByTag = new Map();
      data.forEach((pos: Position) => {
        const existing = latestByTag.get(pos.tag_id);
        if (!existing || new Date(pos.timestamp) > new Date(existing.timestamp)) {
          latestByTag.set(pos.tag_id, pos);
        }
      });
      
      const positionsArray = Array.from(latestByTag.values());
      console.log('[DEBUG] Setting positions:', positionsArray.length, 'unique positions', positionsArray);
      
      setPositions(positionsArray);
    } catch (error) {
      console.error('Error fetching positions:', error);
    }
  };

  const fetchItems = async () => {
    try {
      // Fetch all items with positions - no limit needed, items persist once detected
      const response = await fetch(`${API_URL}/data/items`);
      const data = await response.json();
      
      // Get all items with valid positions (both present and missing)
      // The StoreMap component will render them differently based on status
      // Use explicit null/undefined check since 0 is a valid position
      const itemsWithPositions = data.filter((item: any) => 
        item.x_position !== null && 
        item.x_position !== undefined &&
        item.y_position !== null &&
        item.y_position !== undefined
      );
      
      setItems(itemsWithPositions);
    } catch (error) {
      console.error('Error fetching items:', error);
    }
  };
  
  const fetchStoreConfig = async () => {
    try {
      const response = await fetch(`${API_URL}/config/store`);
      const config = await response.json();
      setMaxDisplayItems(config.max_display_items || 500);
    } catch (error) {
      console.error('Error fetching store config:', error);
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
      console.log('Stock heatmap data:', data);
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
        // Poll the status to confirm the simulation has stopped
        // State should update immediately on backend, just verify
        let attempts = 0;
        const maxAttempts = 4;  // Reduced to 4 attempts
        while (attempts < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, 250));  // 250ms between checks
          const statusResponse = await fetch(`${API_URL}/simulation/status`);
          const status = await statusResponse.json();
          if (!status.running) {
            setSimulationRunning(false);
            await fetchMode();
            return;
          }
          attempts++;
        }
        // If still running after polling, show warning but update state anyway
        console.warn('Simulation may still be stopping...');
        await fetchMode();
      } else {
        alert(data.message || 'Failed to stop simulation');
      }
    } catch (error) {
      alert('Failed to stop simulation');
    }
  };

  const sendHardwareControl = async (command: 'START' | 'STOP') => {
    try {
      const response = await fetch(`${API_URL}/config/mqtt/control?command=${command}`, { 
        method: 'POST' 
      });
      const data = await response.json();
      if (data.success) {
        setHardwareActive(command === 'START');
      } else {
        alert(data.message || `Failed to ${command.toLowerCase()} hardware`);
      }
    } catch (error) {
      alert(`Failed to ${command.toLowerCase()} hardware`);
    }
  };

  const toggleLiveStatus = () => {
    if (currentMode === 'PRODUCTION') {
      // In production mode: control ESP32 hardware
      sendHardwareControl(hardwareActive ? 'STOP' : 'START');
    }
    // In simulation mode: indicator is read-only (shows WebSocket reception status)
  };



  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    
    // Clear results if query is too short
    if (query.trim().length < 2) {
      setSearchResults([]);
      setHighlightedItem(null);
      return;
    }

    try {
      // Validate API_URL is set
      if (!API_URL) {
        console.error('API_URL is not configured. Please set NEXT_PUBLIC_API_URL environment variable.');
        setSearchResults([]);
        return;
      }

      const searchUrl = `${API_URL}/search/items?q=${encodeURIComponent(query)}`;
      console.log('[DEBUG] Search request:', searchUrl);
      
      const response = await fetch(searchUrl);
      
      if (!response.ok) {
        console.error(`Search failed with status ${response.status}: ${response.statusText}`);
        setSearchResults([]);
        return;
      }
      
      const data = await response.json();
      console.log('[DEBUG] Search results:', data);
      setSearchResults(data.items || []);
    } catch (error) {
      // Log error details separately to avoid serialization issues
      console.error('=== SEARCH ERROR ===');
      console.error('API URL:', API_URL);
      console.error('Query:', query);
      console.error('Error Type:', error?.constructor?.name);
      
      if (error instanceof Error) {
        console.error('Error Message:', error.message);
        console.error('Error Stack:', error.stack);
      } else {
        console.error('Error Value:', error);
      }
      
      // Network-specific error messages
      if (error instanceof TypeError) {
        console.error('⚠️ NETWORK/FETCH ERROR: Cannot reach the backend API');
        console.error('Possible causes:');
        console.error('  • Backend not running on', API_URL);
        console.error('  • CORS configuration issue');
        console.error('  • Network connectivity problem');
        console.error('  • Environment variable not loaded (check browser dev tools)');
      }
      console.error('===================');
      
      setSearchResults([]);
    }
  };

  const handleItemClick = async (rfidTag: string) => {
    try {
      const response = await fetch(`${API_URL}/items/${rfidTag}`);
      
      if (!response.ok) {
        console.error(`Failed to fetch item ${rfidTag}: ${response.status} ${response.statusText}`);
        return;
      }
      
      const data = await response.json();
      setSelectedItem(data);
      setHighlightedItem(rfidTag);
      setActivePanel(null); // Show item detail
    } catch (error) {
      console.error('Error fetching item details:', {
        error,
        rfidTag,
        message: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  useEffect(() => {
    const init = async () => {
      // Log environment configuration for debugging
      console.log('[DEBUG] Environment configuration:', {
        API_URL,
        WS_URL,
        hasApiUrl: !!API_URL,
        hasWsUrl: !!WS_URL,
      });
      
      // Validate API connectivity
      if (!API_URL) {
        console.error('CRITICAL: API_URL is not configured. Please set NEXT_PUBLIC_API_URL environment variable.');
        setLoading(false);
        return;
      }
      
      await fetchStoreConfig(); // Fetch config first to get max_display_items
      await fetchAnchors();
      await fetchPositions(); // Initial fetch
      await fetchItems(); // Initial fetch
      await fetchMissingItems();
      await fetchProducts();
      await fetchMode();
      setLoading(false);
    };
    init();
  }, []);

  // Periodically refresh store config (every 10 seconds)
  useEffect(() => {
    const interval = setInterval(fetchStoreConfig, 10000);
    return () => clearInterval(interval);
  }, []);

  // Removed polling interval - now using WebSocket for real-time updates
  // WebSocket automatically updates positions and items as they arrive

  useEffect(() => {
    if (viewMode === 'stock-heatmap') fetchStockHeatmap();
  }, [viewMode]);

  // Poll heatmap data while in heatmap view (every 2 seconds)
  useEffect(() => {
    if (viewMode !== 'stock-heatmap') return;
    
    const interval = setInterval(() => {
      fetchStockHeatmap();
    }, 2000);
    
    return () => clearInterval(interval);
  }, [viewMode]);

  // Generate proper MAC address format: 0x0001, 0x0002, ..., 0x000A, 0x000B, etc.
  const generateMacAddress = (index: number): string => {
    const hex = (index + 1).toString(16).toUpperCase().padStart(4, '0');
    return `0x${hex}`;
  };

  const handleAnchorPlace = async (x: number, y: number, index: number) => {
    if (currentMode === 'PRODUCTION') {
      // In PRODUCTION mode, show modal with pre-filled sequential MAC address
      const suggestedMac = generateMacAddress(index);
      setPendingAnchor({ x, y, index });
      setAnchorMacInput(suggestedMac);
      setAnchorNameInput(`Anchor ${index + 1}`);
      return;
    }
    
    // In SIMULATION mode, auto-generate MAC address
    const anchorData = {
      mac_address: generateMacAddress(index),
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

  const handleConfirmAnchorPlacement = async () => {
    if (!pendingAnchor || !anchorMacInput.trim()) return;
    
    // Normalize MAC address format (ensure it starts with 0x, uppercase hex digits only)
    let macAddress = anchorMacInput.trim();
    if (macAddress.toLowerCase().startsWith('0x')) {
      macAddress = '0x' + macAddress.slice(2).toUpperCase();
    } else {
      macAddress = '0x' + macAddress.toUpperCase();
    }
    
    const anchorData = {
      mac_address: macAddress,
      name: anchorNameInput.trim() || `Anchor ${pendingAnchor.index + 1}`,
      x_position: Math.round(pendingAnchor.x),
      y_position: Math.round(pendingAnchor.y),
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
        setPendingAnchor(null);
        setAnchorMacInput('');
        setAnchorNameInput('');
      } else {
        const error = await response.json();
        alert(`Failed to create anchor: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to create anchor:', error);
      alert('Failed to create anchor. Check console for details.');
    }
  };

  const handleCancelAnchorPlacement = () => {
    setPendingAnchor(null);
    setAnchorMacInput('');
    setAnchorNameInput('');
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

  const handleClearData = () => {
    setShowClearDataModal(true);
  };

  const confirmClearData = async () => {
    setShowClearDataModal(false);
    try {
      await fetch(`${API_URL}/data/clear?delete_items=true`, { method: 'DELETE' });
      
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
    { label: 'Items', value: items.length, status: 'good' },
    { label: 'Missing', value: missingItems.length, status: missingItems.length > 0 ? 'alert' : 'good' },
  ];

  return (
    <div className="h-screen bg-white overflow-hidden">
      <header className="bg-white border-b border-gray-200">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <img src="/logo.png" alt="OptiFlow" className="h-20 w-auto" />
              <div>
                <h1 className="text-3xl font-bold text-gray-900">OptiFlow</h1>
                <p className="text-gray-600 mt-1">Real-time Store Tracking System</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {!setupMode ? (
                <>
                  <a
                    href="/analytics"
                    className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-[#0055A4] hover:bg-gray-50 border border-gray-300 transition-colors"
                  >
                    Analytics
                  </a>
                  <a
                    href="/admin"
                    className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-[#0055A4] hover:bg-gray-50 border border-gray-300 transition-colors"
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
                  {!(currentMode === 'PRODUCTION' ? hardwareActive : (receivingData && wsConnected)) && (
                    <button
                      onClick={() => setSetupMode(true)}
                      className="p-2 text-gray-700 hover:text-[#0055A4] hover:bg-gray-50 border border-gray-300 transition-colors"
                      title="Setup Mode - Place Anchors"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                    </button>
                  )}
                </>
              ) : (
                <>
                  <button
                    onClick={() => setSetupMode(false)}
                    className="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 transition-colors"
                  >
                    Finish Setup
                  </button>
                  <button 
                    onClick={handleResetAnchors} 
                    className="px-4 py-2 text-sm font-medium text-red-600 border border-red-200 hover:bg-red-50 transition-colors"
                  >
                    Reset Anchors
                  </button>
                  {currentMode === 'PRODUCTION' && (
                    <button 
                      onClick={handleClearData} 
                      className="px-4 py-2 text-sm font-medium text-red-600 border border-red-200 hover:bg-red-50 transition-colors"
                    >
                      Clear Data
                    </button>
                  )}
                </>
              )}
              
              <button
                onClick={() => setShowSidebar(!showSidebar)}
                className="p-2 text-gray-700 hover:text-[#0055A4] hover:bg-gray-50 border border-gray-300 transition-colors"
                title={showSidebar ? 'Hide Panels' : 'Show Panels'}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {showSidebar ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                  )}
                </svg>
              </button>
              
              <button
                onClick={toggleLiveStatus}
                disabled={currentMode === 'SIMULATION'}
                className={`flex items-center gap-2 px-3 py-1.5 border transition-all ${
                  currentMode === 'PRODUCTION'
                    ? (hardwareActive 
                      ? 'border-green-200 bg-green-50 hover:bg-green-100 cursor-pointer' 
                      : 'border-red-200 bg-red-50 hover:bg-red-100 cursor-pointer')
                    : (receivingData && wsConnected
                      ? 'border-green-200 bg-green-50' 
                      : 'border-red-200 bg-red-50')
                } ${currentMode === 'SIMULATION' ? 'cursor-default' : ''}`}
                title={
                  currentMode === 'PRODUCTION'
                    ? (hardwareActive ? 'Click to stop ESP32 hardware' : 'Click to start ESP32 hardware')
                    : (receivingData && wsConnected ? 'Receiving live data from WebSocket' : 'No data reception')
                }
              >
                <div className={`w-2 h-2 rounded-full ${
                  currentMode === 'PRODUCTION'
                    ? (hardwareActive ? 'bg-green-500' : 'bg-red-500')
                    : (receivingData && wsConnected ? 'bg-green-500' : 'bg-red-500')
                }`}></div>
                <span className={`text-sm font-medium ${
                  currentMode === 'PRODUCTION'
                    ? (hardwareActive ? 'text-green-700' : 'text-red-700')
                    : (receivingData && wsConnected ? 'text-green-700' : 'text-red-700')
                }`}>
                  {currentMode === 'PRODUCTION'
                    ? (hardwareActive ? 'LIVE' : 'OFFLINE')
                    : (receivingData && wsConnected ? 'LIVE' : 'OFFLINE')
                  }
                </span>
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
                <>
                  {!selectedItem ? (
                    <div className="p-4">
                      {missingItems.length === 0 ? (
                        <div className="text-center py-12 text-gray-500">
                          <div className="text-4xl mb-2">✓</div>
                          <p className="text-sm">All items in stock</p>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {missingItems.map((item, index) => (
                            <div
                              key={item.product_id}
                              className="border-l-4 border-red-500 bg-white hover:bg-gray-50 transition-colors cursor-pointer"
                              onClick={async () => {
                                try {
                                  const response = await fetch(`${API_URL}/items/${item.product_id}`);
                                  const data = await response.json();
                                  setSelectedItem(data);
                                  setHighlightedItem(item.product_id);
                                  // Keep activePanel='missing' so the restock panel stays active
                                } catch (error) {
                                  console.error('Error fetching item details:', error);
                                }
                              }}
                            >
                              <div className="p-3">
                                <div className="flex items-center gap-3">
                                  <span className="text-xs font-bold text-red-600 bg-red-100 px-2 py-1 rounded">HIGH</span>
                                  <span className="text-sm font-semibold text-gray-900">
                                    {item.product_name}
                                  </span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                <div className="p-4">
                  <div className="mb-3">
                    <button
                      onClick={() => {
                        setSelectedItem(null);
                        setHighlightedItem(null);
                        setActivePanel('missing');
                      }}
                      className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                      </svg>
                      Back to List
                    </button>
                  </div>
                  
                  <h3 className="text-xl font-bold text-gray-900 mb-3">{selectedItem.name}</h3>
                  
                  <div className="space-y-3">
                    {/* Product Details */}
                    <div className="border border-gray-200 bg-gray-50 p-3 rounded-lg">
                      <div className="text-xs text-gray-500 uppercase font-semibold mb-2">Product Details</div>
                      <div className="text-sm text-gray-900 space-y-1">
                        {selectedItem.category && (
                          <div className="flex justify-between">
                            <span className="text-gray-500">Category:</span>
                            <span className="font-medium">{selectedItem.category}</span>
                          </div>
                        )}
                        {selectedItem.sku && (
                          <div className="flex justify-between">
                            <span className="text-gray-500">SKU:</span>
                            <span className="font-mono text-xs">{selectedItem.sku}</span>
                          </div>
                        )}
                        {selectedItem.size && (
                          <div className="flex justify-between">
                            <span className="text-gray-500">Size:</span>
                            <span className="font-medium">{selectedItem.size}</span>
                          </div>
                        )}
                        {selectedItem.color && (
                          <div className="flex justify-between">
                            <span className="text-gray-500">Color:</span>
                            <span className="font-medium">{selectedItem.color}</span>
                          </div>
                        )}
                        {selectedItem.unit_price !== null && selectedItem.unit_price !== undefined && (
                          <div className="flex justify-between">
                            <span className="text-gray-500">Price:</span>
                            <span className="font-bold text-[#0055A4]">CHF {selectedItem.unit_price.toFixed(2)}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Stock Information */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="border-2 border-gray-200 bg-white p-3 rounded-lg">
                        <div className="text-xs text-gray-500 uppercase font-semibold mb-1">Currently In Stock</div>
                        <div className="text-2xl font-bold text-green-600">
                          {selectedItem.inventory_summary?.in_stock || 0}
                        </div>
                      </div>
                      
                      <div className="border-2 border-gray-200 bg-white p-3 rounded-lg">
                        <div className="text-xs text-gray-500 uppercase font-semibold mb-1">Max Detected</div>
                        <div className="text-2xl font-bold text-gray-900">
                          {selectedItem.inventory_summary?.max_detected || 0}
                        </div>
                      </div>
                    </div>
                    
                    {selectedItem.inventory_summary?.missing > 0 && (
                      <div className="bg-red-50 border-2 border-red-200 p-3 rounded-lg">
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
                    
                    <div className="border border-gray-200 bg-gray-50 p-3 rounded-lg">
                      <div className="text-xs text-gray-500 uppercase font-semibold mb-1">Last Known Location</div>
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
                      <div className="border border-gray-200 bg-gray-50 p-3 rounded-lg">
                        <div className="text-xs text-gray-500 uppercase font-semibold mb-1">Last Seen</div>
                        <div className="text-sm text-gray-900">
                          {new Date(selectedItem.last_seen).toLocaleString()}
                        </div>
                      </div>
                    )}
                    
                    <div className="pt-1">
                      <div className="text-xs text-gray-400 font-mono text-center">
                        {selectedItem.rfid_tag}
                      </div>
                    </div>
                  </div>
                </div>
                  )}
                </>
              )}

              {selectedItem && activePanel !== 'missing' && (
                <div className="p-4 border-b border-gray-200 bg-white">
                  <div className="mb-3">
                    <button
                      onClick={() => {
                        setSelectedItem(null);
                        setHighlightedItem(null);
                      }}
                      className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                      </svg>
                      Back
                    </button>
                  </div>
                  
                  <h3 className="text-xl font-bold text-gray-900 mb-3">{selectedItem.name}</h3>
                  
                  <div className="space-y-3">
                    {/* Product Details */}
                    <div className="border border-gray-200 bg-gray-50 p-3 rounded-lg">
                      <div className="text-xs text-gray-500 uppercase font-semibold mb-2">Product Details</div>
                      <div className="text-sm text-gray-900 space-y-1">
                        {selectedItem.category && (
                          <div className="flex justify-between">
                            <span className="text-gray-500">Category:</span>
                            <span className="font-medium">{selectedItem.category}</span>
                          </div>
                        )}
                        {selectedItem.sku && (
                          <div className="flex justify-between">
                            <span className="text-gray-500">SKU:</span>
                            <span className="font-mono text-xs">{selectedItem.sku}</span>
                          </div>
                        )}
                        {selectedItem.size && (
                          <div className="flex justify-between">
                            <span className="text-gray-500">Size:</span>
                            <span className="font-medium">{selectedItem.size}</span>
                          </div>
                        )}
                        {selectedItem.color && (
                          <div className="flex justify-between">
                            <span className="text-gray-500">Color:</span>
                            <span className="font-medium">{selectedItem.color}</span>
                          </div>
                        )}
                        {selectedItem.unit_price !== null && selectedItem.unit_price !== undefined && (
                          <div className="flex justify-between">
                            <span className="text-gray-500">Price:</span>
                            <span className="font-bold text-[#0055A4]">CHF {selectedItem.unit_price.toFixed(2)}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Stock Information */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="border-2 border-gray-200 bg-white p-3 rounded-lg">
                        <div className="text-xs text-gray-500 uppercase font-semibold mb-1">Currently In Stock</div>
                        <div className="text-2xl font-bold text-green-600">
                          {selectedItem.inventory_summary?.in_stock || 0}
                        </div>
                      </div>
                      
                      <div className="border-2 border-gray-200 bg-white p-3 rounded-lg">
                        <div className="text-xs text-gray-500 uppercase font-semibold mb-1">Max Detected</div>
                        <div className="text-2xl font-bold text-gray-900">
                          {selectedItem.inventory_summary?.max_detected || 0}
                        </div>
                      </div>
                    </div>
                    
                    {selectedItem.inventory_summary?.missing > 0 && (
                      <div className="bg-red-50 border-2 border-red-200 p-3 rounded-lg">
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
                    
                    <div className="border border-gray-200 bg-gray-50 p-3 rounded-lg">
                      <div className="text-xs text-gray-500 uppercase font-semibold mb-1">Last Known Location</div>
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
                      <div className="border border-gray-200 bg-gray-50 p-3 rounded-lg">
                        <div className="text-xs text-gray-500 uppercase font-semibold mb-1">Last Seen</div>
                        <div className="text-sm text-gray-900">
                          {new Date(selectedItem.last_seen).toLocaleString()}
                        </div>
                      </div>
                    )}
                    
                    <div className="pt-1">
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
      </div>

      {/* Anchor Placement Modal for PRODUCTION mode */}
      {pendingAnchor && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-[420px] max-w-[90vw]">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-[#0055A4] rounded-full flex items-center justify-center text-white font-bold">
                {pendingAnchor.index + 1}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Configure Anchor {pendingAnchor.index + 1}
                </h3>
                <p className="text-xs text-gray-500">Position: ({Math.round(pendingAnchor.x)}, {Math.round(pendingAnchor.y)}) cm</p>
              </div>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  MAC Address <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={anchorMacInput}
                  onChange={(e) => setAnchorMacInput(e.target.value)}
                  placeholder="e.g., 0x0001"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0055A4] focus:border-transparent text-sm font-mono text-lg"
                  autoFocus
                />
                <p className="text-xs text-gray-500 mt-1">
                  Pre-filled with sequential address. Change to match your DWM3001CDK device if needed.
                </p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Anchor Name
                </label>
                <input
                  type="text"
                  value={anchorNameInput}
                  onChange={(e) => setAnchorNameInput(e.target.value)}
                  placeholder="e.g., Corner NW"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0055A4] focus:border-transparent text-sm"
                />
              </div>
              
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
                <div className="font-medium mb-1">💡 Tip</div>
                Place anchors at known physical locations (e.g., room corners). 
                The position should match where the anchor is in the real world.
              </div>
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={handleCancelAnchorPlacement}
                className="flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAnchorPlacement}
                disabled={!anchorMacInput.trim()}
                className="flex-1 px-4 py-2.5 text-sm font-medium text-white bg-[#0055A4] rounded-lg hover:bg-[#003d7a] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                Create Anchor
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Clear Data Confirmation Modal */}
      {showClearDataModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              Clear All Tracking Data?
            </h3>
            <p className="text-gray-600 mb-6">
              This will remove all item positions and tracking data. Anchors and products will be preserved.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowClearDataModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmClearData}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
              >
                Clear Data
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
