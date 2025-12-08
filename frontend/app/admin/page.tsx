'use client';

import React, { useState, useEffect } from 'react';
import type { Anchor, Product, StoreConfig, ModeResponse, SimulationStatus, AnchorValidation, ConfigMode } from '@/src/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

export default function AdminPanel() {
  const [activeTab, setActiveTab] = useState<'mode' | 'anchors' | 'products' | 'store' | 'system'>('mode');
  const [mode, setMode] = useState<ModeResponse | null>(null);
  const [storeConfig, setStoreConfig] = useState<StoreConfig | null>(null);
  const [simulationStatus, setSimulationStatus] = useState<SimulationStatus | null>(null);
  const [anchors, setAnchors] = useState<Anchor[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [validation, setValidation] = useState<AnchorValidation | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [changedProducts, setChangedProducts] = useState<Map<number, any>>(new Map());
  const [expandedProducts, setExpandedProducts] = useState<Set<number>>(new Set());
  const [productItems, setProductItems] = useState<Map<number, any[]>>(new Map());
  const [simSpeedMultiplier, setSimSpeedMultiplier] = useState<number>(1.0);
  const [simMode, setSimMode] = useState<string>('REALISTIC');
  const [simDisappearanceRate, setSimDisappearanceRate] = useState<number>(1.5);
  const [simItemCount, setSimItemCount] = useState<number>(1000);
  const [regeneratingInventory, setRegeneratingInventory] = useState(false);
  const [showClearDataModal, setShowClearDataModal] = useState(false);
  const [productSearch, setProductSearch] = useState<string>('');
  const [productFilter, setProductFilter] = useState<string>('all');
  const [productSort, setProductSort] = useState<string>('name');
  const [connectionStatus, setConnectionStatus] = useState<any>(null);
  const [checkingConnection, setCheckingConnection] = useState(false);
  const [pendingModeSwitch, setPendingModeSwitch] = useState<ConfigMode | null>(null);
  
  // Anchor management state
  const [showAnchorForm, setShowAnchorForm] = useState(false);
  const [editingAnchor, setEditingAnchor] = useState<Anchor | null>(null);
  const [anchorForm, setAnchorForm] = useState({
    mac_address: '',
    name: '',
    x_position: 0,
    y_position: 0,
    is_active: true
  });

  // Fetch initial data
  useEffect(() => {
    fetchMode();
    fetchStoreConfig();
    fetchSimulationStatus();
    fetchAnchors();
    fetchProducts();
  }, []);

  // Auto-refresh simulation status
  useEffect(() => {
    const interval = setInterval(() => {
      if (mode?.mode === 'SIMULATION') {
        fetchSimulationStatus();
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [mode]);

  const showMessage = (type: 'success' | 'error' | 'info', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  const fetchMode = async () => {
    try {
      const res = await fetch(`${API_URL}/config/mode`);
      const data = await res.json();
      setMode(data);
    } catch (error) {
      console.error('Failed to fetch mode:', error);
    }
  };

  const fetchStoreConfig = async () => {
    try {
      const res = await fetch(`${API_URL}/config/store`);
      const data = await res.json();
      setStoreConfig(data);
    } catch (error) {
      console.error('Failed to fetch store config:', error);
    }
  };

  const fetchSimulationStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/simulation/status`);
      const data = await res.json();
      setSimulationStatus(data);
    } catch (error) {
      console.error('Failed to fetch simulation status:', error);
    }
  };

  const fetchAnchors = async () => {
    try {
      const res = await fetch(`${API_URL}/anchors`);
      const data = await res.json();
      setAnchors(data);
    } catch (error) {
      console.error('Failed to fetch anchors:', error);
    }
  };

  const fetchProducts = async () => {
    try {
      const res = await fetch(`${API_URL}/products/with-stock`);
      const data = await res.json();
      setProducts(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to fetch products:', error);
      setProducts([]);
    }
  };

  const updateProduct = async (productId: number, updates: Partial<Product>) => {
    setLoading(true);
    try {
      const product = products.find(p => p.id === productId);
      if (!product) return;
      
      const res = await fetch(`${API_URL}/products/${productId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sku: updates.sku ?? product.sku,
          name: updates.name ?? product.name,
          category: updates.category ?? product.category,
          unit_price: updates.unit_price ?? product.unit_price,
          reorder_threshold: updates.reorder_threshold !== undefined ? updates.reorder_threshold : product.reorder_threshold,
          optimal_stock_level: updates.optimal_stock_level ?? product.optimal_stock_level
        })
      });
      
      if (res.ok) {
        showMessage('success', 'Product updated successfully');
        await fetchProducts();
      } else {
        const error = await res.json();
        showMessage('error', error.detail || 'Failed to update product');
      }
    } catch (error) {
      showMessage('error', 'Failed to update product');
    } finally {
      setLoading(false);
    }
  };

  const adjustStock = async (productId: number, currentStock: number, maxDetected: number) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/products/${productId}/adjust-stock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_stock: currentStock,
          max_detected: maxDetected
        })
      });
      
      if (res.ok) {
        showMessage('success', 'Stock adjusted successfully');
        await fetchProducts();
      } else {
        const error = await res.json();
        showMessage('error', error.detail || 'Failed to adjust stock');
      }
    } catch (error) {
      showMessage('error', 'Failed to adjust stock');
    } finally {
      setLoading(false);
    }
  };

  const trackProductChange = (productId: number, field: string, value: any) => {
    setChangedProducts(prev => {
      const newMap = new Map(prev);
      const existing = newMap.get(productId) || {};
      newMap.set(productId, { ...existing, [field]: value });
      return newMap;
    });
  };

  const toggleProductExpand = async (productId: number) => {
    const newExpanded = new Set(expandedProducts);
    
    if (newExpanded.has(productId)) {
      newExpanded.delete(productId);
      setExpandedProducts(newExpanded);
    } else {
      // Fetch items for this product if not already loaded
      if (!productItems.has(productId)) {
        try {
          const res = await fetch(`${API_URL}/products/${productId}/items`);
          if (res.ok) {
            const items = await res.json();
            setProductItems(prev => new Map(prev).set(productId, items));
          }
        } catch (error) {
          console.error('Failed to fetch product items:', error);
        }
      }
      newExpanded.add(productId);
      setExpandedProducts(newExpanded);
    }
  };

  const deleteItem = async (rfidTag: string, productId: number) => {
    if (!confirm(`Delete item ${rfidTag}? This cannot be undone.`)) {
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/items/${rfidTag}`, {
        method: 'DELETE'
      });

      if (res.ok) {
        showMessage('success', `Item ${rfidTag} deleted`);
        // Refresh the items for this product
        const itemsRes = await fetch(`${API_URL}/products/${productId}/items`);
        if (itemsRes.ok) {
          const items = await itemsRes.json();
          setProductItems(prev => new Map(prev).set(productId, items));
        }
        // Refresh products to update counts
        await fetchProducts();
      } else {
        const error = await res.json();
        showMessage('error', error.detail || 'Failed to delete item');
      }
    } catch (error) {
      showMessage('error', 'Failed to delete item');
    } finally {
      setLoading(false);
    }
  };

  const checkConnectionStatus = async () => {
    setCheckingConnection(true);
    try {
      const res = await fetch(`${API_URL}/simulation/connection-status`);
      const data = await res.json();
      setConnectionStatus(data);
      return data;
    } catch (error) {
      console.error('Failed to check connection status:', error);
      return null;
    } finally {
      setCheckingConnection(false);
    }
  };

  const saveAllChanges = async () => {
    if (changedProducts.size === 0) {
      showMessage('info', 'No changes to save');
      return;
    }

    setLoading(true);
    let successCount = 0;
    let errorCount = 0;

    for (const [productId, changes] of changedProducts.entries()) {
      try {
        const product = products.find(p => p.id === productId);
        if (!product) continue;

        // Only handle product field updates (no manual stock adjustments)
        const productUpdates: any = {};
        if (changes.sku !== undefined) productUpdates.sku = changes.sku;
        if (changes.name !== undefined) productUpdates.name = changes.name;
        if (changes.category !== undefined) productUpdates.category = changes.category;
        if (changes.unit_price !== undefined) productUpdates.unit_price = changes.unit_price;
        if (changes.reorder_threshold !== undefined) productUpdates.reorder_threshold = changes.reorder_threshold;
        if (changes.optimal_stock_level !== undefined) productUpdates.optimal_stock_level = changes.optimal_stock_level;

        if (Object.keys(productUpdates).length > 0) {
          await updateProduct(productId, productUpdates);
        }

        successCount++;
      } catch (error) {
        errorCount++;
      }
    }

    setChangedProducts(new Map());
    setEditMode(false);
    setLoading(false);

    if (errorCount > 0) {
      showMessage('error', `Saved ${successCount} products, ${errorCount} failed`);
    } else {
      showMessage('success', `Successfully saved ${successCount} products`);
    }

    await fetchProducts();
  };

  const switchMode = (newMode: ConfigMode) => {
    // Show confirmation modal instead of browser confirm()
    setPendingModeSwitch(newMode);
  };

  const confirmModeSwitch = async () => {
    if (!pendingModeSwitch) return;
    
    const newMode = pendingModeSwitch;
    setPendingModeSwitch(null);
    setLoading(true);
    
    try {
      const res = await fetch(`${API_URL}/config/mode/switch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode, confirm: true })
      });
      
      const data = await res.json();
      
      if (res.ok) {
        showMessage('success', data.message);
        await fetchMode();
        await fetchSimulationStatus();
      } else {
        showMessage('error', data.detail || 'Failed to switch mode');
      }
    } catch (error) {
      console.error('Switch mode error:', error);
      showMessage('error', 'Failed to switch mode');
    } finally {
      setLoading(false);
    }
  };

  const startSimulation = async () => {
    setLoading(true);
    
    try {
      // Check connection status first
      const status = await checkConnectionStatus();
      
      if (!status) {
        showMessage('error', 'Failed to check connection status');
        setLoading(false);
        return;
      }
      
      // Check MQTT connection
      if (!status.mqtt_connected) {
        const errorMsg = status.mqtt_error || `Cannot connect to MQTT broker at ${status.mqtt_broker}`;
        const wifiInfo = status.wifi_ssid ? ` (Currently on WiFi: ${status.wifi_ssid})` : '';
        showMessage('error', `MQTT Connection Failed: ${errorMsg}${wifiInfo}. Make sure you're connected to the correct network (e.g., 'Oscar' hotspot) and the MQTT broker is running.`);
        setLoading(false);
        return;
      }
      
      // All checks passed, start simulation
      const res = await fetch(`${API_URL}/simulation/start`, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          speed_multiplier: simSpeedMultiplier,
          mode: simMode,
          disappearance_rate: simDisappearanceRate / 100  // Convert percentage to decimal
        })
      });
      const data = await res.json();
      
      if (res.ok && data.success) {
        showMessage('success', `Simulation started (${simMode} mode, ${simSpeedMultiplier}x speed)`);
        await fetchSimulationStatus();
      } else {
        showMessage('error', data.message || data.detail || 'Failed to start simulation');
      }
    } catch (error) {
      showMessage('error', 'Failed to start simulation');
    } finally {
      setLoading(false);
    }
  };

  const stopSimulation = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/simulation/stop`, { method: 'POST' });
      const data = await res.json();
      
      if (res.ok) {
        showMessage('success', 'Simulation stopped');
        await fetchSimulationStatus();
      } else {
        showMessage('error', 'Failed to stop simulation');
      }
    } catch (error) {
      showMessage('error', 'Failed to stop simulation');
    } finally {
      setLoading(false);
    }
  };

  const handleClearAllData = async () => {
    setShowClearDataModal(false);
    setLoading(true);
    try {
      // Delete all items and products for a fresh start
      const res = await fetch(`${API_URL}/data/clear?delete_items=true`, { method: 'DELETE' });
      const data = await res.json();
      
      if (res.ok) {
        showMessage('success', 'All data cleared successfully');
        // Refresh products list
        await fetchProducts();
      } else {
        showMessage('error', data.detail || 'Failed to clear data');
      }
    } catch (error) {
      showMessage('error', 'Failed to clear data');
    } finally {
      setLoading(false);
    }
  };

  const regenerateInventory = async () => {
    setRegeneratingInventory(true);
    try {
      // Call the backend to generate inventory
      const res = await fetch(`${API_URL}/simulation/generate-inventory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_count: simItemCount })
      });
      const data = await res.json();
      
      if (res.ok) {
        showMessage('success', `Generated ${data.items_created || simItemCount} items successfully`);
        // Refresh products list
        await fetchProducts();
      } else {
        showMessage('error', data.detail || 'Failed to generate inventory');
      }
    } catch (error) {
      showMessage('error', 'Failed to generate inventory');
    } finally {
      setRegeneratingInventory(false);
    }
  };

  const validateAnchors = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/config/validate-anchors`);
      const data = await res.json();
      setValidation(data);
      
      if (data.valid) {
        showMessage('success', data.message);
      } else {
        showMessage('info', data.message);
      }
    } catch (error) {
      showMessage('error', 'Failed to validate anchors');
    } finally {
      setLoading(false);
    }
  };

  const updateStoreConfig = async (width?: number, height?: number, maxDisplayItems?: number) => {
    setLoading(true);
    try {
      const body: any = {};
      if (width !== undefined) body.store_width = width;
      if (height !== undefined) body.store_height = height;
      if (maxDisplayItems !== undefined) body.max_display_items = maxDisplayItems;
      
      const res = await fetch(`${API_URL}/config/store`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      
      if (res.ok) {
        showMessage('success', 'Store configuration updated');
        await fetchStoreConfig();
      } else {
        showMessage('error', 'Failed to update store config');
      }
    } catch (error) {
      showMessage('error', 'Failed to update store config');
    } finally {
      setLoading(false);
    }
  };

  const updateAnchor = async (id: number, updates: Partial<Anchor>) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/anchors/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      
      if (res.ok) {
        showMessage('success', 'Anchor updated');
        await fetchAnchors();
      } else {
        showMessage('error', 'Failed to update anchor');
      }
    } catch (error) {
      showMessage('error', 'Failed to update anchor');
    } finally {
      setLoading(false);
    }
  };

  const deleteAnchor = async (id: number) => {
    if (!confirm('Delete this anchor?')) return;
    
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/anchors/${id}`, { method: 'DELETE' });
      
      if (res.ok) {
        showMessage('success', 'Anchor deleted');
        await fetchAnchors();
      } else {
        showMessage('error', 'Failed to delete anchor');
      }
    } catch (error) {
      showMessage('error', 'Failed to delete anchor');
    } finally {
      setLoading(false);
    }
  };

  const openAnchorForm = (anchor?: Anchor) => {
    if (anchor) {
      setEditingAnchor(anchor);
      setAnchorForm({
        mac_address: anchor.mac_address,
        name: anchor.name,
        x_position: anchor.x_position,
        y_position: anchor.y_position,
        is_active: anchor.is_active
      });
    } else {
      setEditingAnchor(null);
      setAnchorForm({
        mac_address: '',
        name: `Anchor ${anchors.length + 1}`,
        x_position: 0,
        y_position: 0,
        is_active: true
      });
    }
    setShowAnchorForm(true);
  };

  const closeAnchorForm = () => {
    setShowAnchorForm(false);
    setEditingAnchor(null);
    setAnchorForm({
      mac_address: '',
      name: '',
      x_position: 0,
      y_position: 0,
      is_active: true
    });
  };

  const saveAnchor = async () => {
    // Normalize MAC address (keep 0x lowercase, uppercase hex digits only)
    let macAddress = anchorForm.mac_address.trim();
    if (macAddress.toLowerCase().startsWith('0x')) {
      macAddress = '0x' + macAddress.slice(2).toUpperCase();
    } else {
      macAddress = '0x' + macAddress.toUpperCase();
    }
    
    const anchorData = {
      ...anchorForm,
      mac_address: macAddress,
      name: anchorForm.name.trim() || `Anchor ${anchors.length + 1}`,
      x_position: Math.round(anchorForm.x_position),
      y_position: Math.round(anchorForm.y_position)
    };

    setLoading(true);
    try {
      const url = editingAnchor 
        ? `${API_URL}/anchors/${editingAnchor.id}` 
        : `${API_URL}/anchors`;
      const method = editingAnchor ? 'PUT' : 'POST';
      
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(anchorData)
      });

      if (res.ok) {
        showMessage('success', editingAnchor ? 'Anchor updated' : 'Anchor created');
        await fetchAnchors();
        closeAnchorForm();
      } else {
        const error = await res.json();
        showMessage('error', error.detail || 'Failed to save anchor');
      }
    } catch (error) {
      showMessage('error', 'Failed to save anchor');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Mode Switch Confirmation Modal */}
      {pendingModeSwitch && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              Switch to {pendingModeSwitch} Mode?
            </h3>
            <p className="text-gray-600 mb-6">
              {pendingModeSwitch === 'REAL' 
                ? 'This will switch to real hardware mode. The simulation will be stopped and the system will listen for data from physical RFID/UWB devices.'
                : 'This will switch to simulation mode. You can run the inventory simulation to test the system.'}
            </p>
            <p className="text-sm text-gray-500 mb-6">
              All data will be preserved and can be resumed by switching back.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setPendingModeSwitch(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmModeSwitch}
                className="px-4 py-2 text-sm font-medium text-white bg-[#0055A4] hover:bg-[#003d7a] rounded-lg transition-colors"
              >
                Switch to {pendingModeSwitch}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">OptiFlow Admin Panel</h1>
            <p className="text-gray-600 mt-1">System configuration and management</p>
          </div>
          <a
            href="/"
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-[#0055A4] hover:bg-gray-50 border border-gray-300 rounded-lg transition-colors flex items-center gap-2"
          >
            ← Back to Dashboard
          </a>
        </div>

        {message && (
          <div className={`mb-4 p-4 rounded-lg ${
            message.type === 'success' ? 'bg-green-50 text-green-800' :
            message.type === 'error' ? 'bg-red-50 text-red-800' :
            'bg-blue-50 text-blue-800'
          }`}>
            {message.text}
          </div>
        )}

        {/* Tab Navigation */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              {[
                { id: 'mode', label: 'Mode Control' },
                { id: 'anchors', label: 'Anchors' },
                { id: 'products', label: 'Products' },
                { id: 'store', label: 'Store Config' },
                { id: 'system', label: 'System Info' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'border-[#0055A4] text-[#0055A4]'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          <div className="p-6">
            {/* Mode Control Tab */}
            {activeTab === 'mode' && (
              <div className="space-y-3">
                <div>
                  <h2 className="text-lg font-semibold mb-2">Operating Mode</h2>
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-xs text-gray-600 font-medium">Current:</span>
                    <span className={`px-3 py-1 rounded-lg font-semibold text-xs ${
                      mode?.mode === 'SIMULATION' 
                        ? 'bg-blue-100 text-blue-800 border border-blue-200' 
                        : 'bg-green-100 text-green-800 border border-green-200'
                    }`}>
                      {mode?.mode || 'Loading...'}
                    </span>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => switchMode('SIMULATION')}
                      disabled={mode?.mode === 'SIMULATION' || loading}
                      className="px-4 py-2 text-xs font-medium bg-[#0055A4] text-white rounded-lg hover:bg-[#003d7a] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                    >
                      Simulation Mode
                    </button>
                    <button
                      onClick={() => switchMode('REAL')}
                      disabled={mode?.mode === 'REAL' || loading}
                      className="px-4 py-2 text-xs font-medium bg-[#0055A4] text-white rounded-lg hover:bg-[#003d7a] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                    >
                      Real Hardware
                    </button>
                  </div>
                </div>

                {mode?.mode === 'SIMULATION' && (
                  <div className="border-t pt-4">
                    <h2 className="text-lg font-semibold mb-3">Simulation Control</h2>
                    
                    {/* Parameters Section */}
                    <div className="space-y-3 mb-3">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Number of Items
                          </label>
                          <input
                            type="number"
                            min="50"
                            max="5000"
                            step="50"
                            value={simItemCount}
                            onChange={(e) => {
                              const val = e.target.value;
                              // Allow empty string for easier editing
                              if (val === '') {
                                setSimItemCount('' as any);
                              } else {
                                const numVal = parseInt(val);
                                if (!isNaN(numVal)) {
                                  setSimItemCount(numVal);
                                }
                              }
                            }}
                            onBlur={(e) => {
                              const val = e.target.value;
                              if (val === '' || isNaN(parseInt(val))) {
                                setSimItemCount(1000);
                              } else {
                                const numVal = parseInt(val);
                                if (numVal < 50 || numVal > 5000) {
                                  showMessage('error', 'Item count must be between 50 and 5000');
                                  setSimItemCount(1000);
                                }
                              }
                            }}
                            disabled={simulationStatus?.running || loading || regeneratingInventory}
                            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0055A4] focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                          />
                          <p className="text-xs text-gray-500 mt-0.5">
                            Recommended: 50-5000 items
                          </p>
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Speed: {simSpeedMultiplier}x
                          </label>
                          <input
                            type="range"
                            min="0.5"
                            max="5"
                            step="0.5"
                            value={simSpeedMultiplier}
                            onChange={(e) => setSimSpeedMultiplier(parseFloat(e.target.value))}
                            disabled={simulationStatus?.running || loading}
                            className="w-full h-1.5 bg-gray-300 rounded-lg appearance-none cursor-pointer accent-[#0055A4] disabled:cursor-not-allowed"
                          />
                          <div className="flex justify-between text-xs text-gray-500 mt-0.5 px-0.5">
                            <span>0.5x</span>
                            <span>5x</span>
                          </div>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Disappearance Rate: {simDisappearanceRate}%
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="10"
                          step="0.5"
                          value={simDisappearanceRate}
                          onChange={(e) => setSimDisappearanceRate(parseFloat(e.target.value))}
                          disabled={simulationStatus?.running || loading}
                          className="w-full h-1.5 bg-gray-300 rounded-lg appearance-none cursor-pointer accent-[#0055A4] disabled:cursor-not-allowed"
                        />
                        <div className="flex justify-between text-xs text-gray-500 mt-0.5 px-0.5">
                          <span>0%</span>
                          <span>10%</span>
                        </div>
                      </div>
                    </div>

                    {/* Control Buttons */}
                    <div className="bg-gray-50 rounded-lg p-3 mb-3">
                      <div className="flex flex-wrap gap-2 mb-2">
                        <button
                          onClick={startSimulation}
                          disabled={simulationStatus?.running || loading || checkingConnection}
                          className="px-4 py-2 text-sm font-medium bg-[#0055A4] text-white rounded-lg hover:bg-[#003d7a] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                        >
                          {checkingConnection ? 'Checking...' : 'Start'}
                        </button>
                        <button
                          onClick={stopSimulation}
                          disabled={!simulationStatus?.running || loading}
                          className="px-4 py-2 text-sm font-medium bg-gray-400 text-white rounded-lg hover:bg-gray-500 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                        >
                          Stop
                        </button>
                        <button
                          onClick={checkConnectionStatus}
                          disabled={loading || checkingConnection}
                          className="px-4 py-2 text-sm font-medium bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                        >
                          Test Connection
                        </button>
                        {simulationStatus?.running && (
                          <div className="flex items-center gap-1.5 ml-2">
                            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                            <span className="text-xs text-gray-600 font-medium">Running</span>
                          </div>
                        )}
                      </div>
                      
                      <div className="grid grid-cols-2 gap-2">
                        <button
                          onClick={() => setShowClearDataModal(true)}
                          disabled={simulationStatus?.running || loading}
                          className="px-3 py-1.5 text-xs font-medium bg-gray-600 text-white rounded hover:bg-gray-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                        >
                          Clear Data
                        </button>
                        <button
                          onClick={() => {
                            if (products.length > 0) {
                              showMessage('error', `⚠️ You have ${products.length} existing products. Click "Clear Data" first to start fresh!`);
                              return;
                            }
                            regenerateInventory();
                          }}
                          disabled={simulationStatus?.running || loading || regeneratingInventory}
                          className="px-3 py-1.5 text-xs font-medium bg-gray-600 text-white rounded hover:bg-gray-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                          title="Generate inventory items (must clear data first if items exist)"
                        >
                          {regeneratingInventory ? 'Generating...' : 'Generate Items'}
                        </button>
                      </div>
                    </div>

                    {connectionStatus && (
                      <div className={`p-3 rounded-lg border text-xs space-y-1 mb-3 ${
                        connectionStatus.mqtt_connected
                          ? 'bg-green-50 border-green-200'
                          : 'bg-red-50 border-red-200'
                      }`}>
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${connectionStatus.mqtt_connected ? 'bg-green-500' : 'bg-red-500'}`}></span>
                          <span className="font-medium">MQTT:</span>
                          <span className="text-gray-600">{connectionStatus.mqtt_broker}</span>
                          <span className={connectionStatus.mqtt_connected ? 'text-green-600 ml-auto' : 'text-red-600 ml-auto'}>
                            {connectionStatus.mqtt_connected ? '✓ Connected' : '✗ Disconnected'}
                          </span>
                        </div>
                        {connectionStatus.mqtt_error && (
                          <div className="text-red-600 ml-4">{connectionStatus.mqtt_error}</div>
                        )}
                        {connectionStatus.wifi_ssid && (
                          <div className="flex items-center gap-2 text-gray-600 ml-4">
                            <span>WiFi: {connectionStatus.wifi_ssid}</span>
                          </div>
                        )}
                      </div>
                    )}

                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-gray-700 leading-relaxed">
                      <strong>How to use:</strong> Set parameters above, then click Start to begin simulation. Sliders can only be adjusted when stopped. The system will auto-check your connection when starting.
                    </div>
                  </div>
                )}

                {/* Clear Data Confirmation Modal */}
                {showClearDataModal && (
                  <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
                      <h3 className="text-xl font-semibold text-gray-900 mb-4">
                        Clear All Simulation Data?
                      </h3>
                      <p className="text-gray-600 mb-4">
                        This will permanently delete all:
                      </p>
                      <ul className="list-disc list-inside text-gray-600 mb-6 text-sm space-y-1">
                        <li>Inventory items and products</li>
                        <li>Detection history</li>
                        <li>Position tracking data</li>
                        <li>Analytics and heatmap data</li>
                      </ul>
                      <p className="text-sm text-orange-600 mb-6">
                        ⚠️ This action cannot be undone.
                      </p>
                      <div className="flex gap-3 justify-end">
                        <button
                          onClick={() => setShowClearDataModal(false)}
                          className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleClearAllData}
                          className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
                        >
                          Delete All Data
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {mode?.mode === 'REAL' && (
                  <div className="border-t pt-3">
                    <h2 className="text-lg font-semibold mb-2">Anchor Validation</h2>
                    <button
                      onClick={validateAnchors}
                      disabled={loading}
                      className="px-4 py-2 text-xs font-medium bg-[#0055A4] text-white rounded-lg hover:bg-[#003d7a] disabled:bg-gray-300 transition-colors mb-2"
                    >
                      Validate Anchors
                    </button>

                    {validation && (
                      <div className={`p-3 rounded-lg text-xs ${
                        validation.valid ? 'bg-green-50 border border-green-200' : 'bg-yellow-50 border border-yellow-200'
                      }`}>
                        <p className="font-medium mb-1">{validation.message}</p>
                        {validation.warnings.length > 0 && (
                          <ul className="list-disc list-inside space-y-0.5 text-xs">
                            {validation.warnings.map((warning: string, i: number) => (
                              <li key={i}>{warning}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Anchors Tab */}
            {activeTab === 'anchors' && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold">Anchor Management</h2>
                  <button
                    onClick={() => openAnchorForm()}
                    className="px-4 py-2 text-sm font-medium text-white bg-[#0055A4] rounded-lg hover:bg-[#003d7a] transition-colors"
                  >
                    + Add Anchor
                  </button>
                </div>
                
                {mode?.mode === 'REAL' && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                    <h4 className="font-medium text-blue-900 mb-2">Real Mode - Hardware Configuration</h4>
                    <p className="text-sm text-blue-800 mb-2">
                      For real mode, you need to enter the actual MAC addresses from your DWM3001CDK devices.
                    </p>
                    <p className="text-sm text-blue-700">
                      <strong>Finding your anchor MAC:</strong> Connect to your DWM3001CDK via USB, open a serial terminal, 
                      and run <code className="bg-blue-100 px-1 rounded">les</code> command to see the device address.
                    </p>
                  </div>
                )}
                
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">MAC Address</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">X (cm)</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Y (cm)</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {anchors.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                            No anchors configured. Click "Add Anchor" to create one, or place anchors on the store map.
                          </td>
                        </tr>
                      ) : (
                        anchors.map((anchor) => (
                          <tr key={anchor.id}>
                            <td className="px-4 py-3 text-sm font-mono">{anchor.mac_address}</td>
                            <td className="px-4 py-3 text-sm">{anchor.name}</td>
                            <td className="px-4 py-3 text-sm">{anchor.x_position.toFixed(0)}</td>
                            <td className="px-4 py-3 text-sm">{anchor.y_position.toFixed(0)}</td>
                            <td className="px-4 py-3 text-sm">
                              <span className={`px-2 py-1 rounded-full text-xs ${
                                anchor.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                              }`}>
                                {anchor.is_active ? 'Active' : 'Inactive'}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-sm space-x-2">
                              <button
                                onClick={() => openAnchorForm(anchor)}
                                className="text-[#0055A4] hover:text-[#003d7a]"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => deleteAnchor(anchor.id)}
                                className="text-red-600 hover:text-red-800"
                              >
                                Delete
                              </button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
                
                {/* Anchor Form Modal */}
                {showAnchorForm && (
                  <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl p-6 w-[450px] max-w-[90vw]">
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">
                        {editingAnchor ? 'Edit Anchor' : 'Add New Anchor'}
                      </h3>
                      
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            MAC Address <span className="text-red-500">*</span>
                          </label>
                          <input
                            type="text"
                            value={anchorForm.mac_address}
                            onChange={(e) => setAnchorForm({...anchorForm, mac_address: e.target.value})}
                            placeholder="e.g., 0xABCD or ABCD"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0055A4] focus:border-transparent text-sm font-mono"
                          />
                          <p className="text-xs text-gray-500 mt-1">
                            {mode?.mode === 'REAL' 
                              ? 'Enter the actual MAC address from your DWM3001CDK device'
                              : 'Format: 0xXXXX (e.g., 0x0001, 0x0002)'}
                          </p>
                        </div>
                        
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Name
                          </label>
                          <input
                            type="text"
                            value={anchorForm.name}
                            onChange={(e) => setAnchorForm({...anchorForm, name: e.target.value})}
                            placeholder="e.g., Anchor 1, Corner NW"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0055A4] focus:border-transparent text-sm"
                          />
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              X Position (cm)
                            </label>
                            <input
                              type="number"
                              value={anchorForm.x_position}
                              onChange={(e) => setAnchorForm({...anchorForm, x_position: parseFloat(e.target.value) || 0})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0055A4] focus:border-transparent text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Y Position (cm)
                            </label>
                            <input
                              type="number"
                              value={anchorForm.y_position}
                              onChange={(e) => setAnchorForm({...anchorForm, y_position: parseFloat(e.target.value) || 0})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0055A4] focus:border-transparent text-sm"
                            />
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            id="anchorActive"
                            checked={anchorForm.is_active}
                            onChange={(e) => setAnchorForm({...anchorForm, is_active: e.target.checked})}
                            className="w-4 h-4 text-[#0055A4] border-gray-300 rounded focus:ring-[#0055A4]"
                          />
                          <label htmlFor="anchorActive" className="text-sm text-gray-700">
                            Active
                          </label>
                        </div>
                      </div>
                      
                      <div className="flex gap-3 mt-6">
                        <button
                          onClick={closeAnchorForm}
                          className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={saveAnchor}
                          disabled={!anchorForm.mac_address.trim() || loading}
                          className="flex-1 px-4 py-2 text-sm font-medium text-white bg-[#0055A4] rounded-lg hover:bg-[#003d7a] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                        >
                          {loading ? 'Saving...' : (editingAnchor ? 'Update' : 'Create')}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Products Tab */}
            {activeTab === 'products' && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold">Product Catalog</h2>
                  <button
                    onClick={() => editMode ? saveAllChanges() : setEditMode(true)}
                    disabled={loading}
                    className={`px-6 py-2 text-sm font-medium text-white rounded-lg transition-colors ${
                      editMode 
                        ? 'bg-green-600 hover:bg-green-700' 
                        : 'bg-[#0055A4] hover:bg-[#003d7a]'
                    } disabled:bg-gray-300 disabled:cursor-not-allowed`}
                  >
                    {editMode ? `Save Changes ${changedProducts.size > 0 ? `(${changedProducts.size})` : ''}` : 'Edit Products'}
                  </button>
                </div>

                {/* Search, Filter, Sort Controls */}
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Search</label>
                    <input
                      type="text"
                      value={productSearch}
                      onChange={(e) => setProductSearch(e.target.value)}
                      placeholder="Search by name, SKU, or category..."
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0055A4] focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Filter</label>
                    <select
                      value={productFilter}
                      onChange={(e) => setProductFilter(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0055A4] focus:border-transparent"
                    >
                      <option value="all">All Products</option>
                      <option value="in-stock">In Stock</option>
                      <option value="low-stock">Low Stock (Below Restock)</option>
                      <option value="out-of-stock">Out of Stock</option>
                      <option value="has-restock">Has Restock Threshold</option>
                      <option value="no-restock">No Restock Threshold</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Sort By</label>
                    <select
                      value={productSort}
                      onChange={(e) => setProductSort(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0055A4] focus:border-transparent"
                    >
                      <option value="name">Name (A-Z)</option>
                      <option value="name-desc">Name (Z-A)</option>
                      <option value="sku">SKU (A-Z)</option>
                      <option value="sku-desc">SKU (Z-A)</option>
                      <option value="category">Category</option>
                      <option value="stock-low">Stock (Low to High)</option>
                      <option value="stock-high">Stock (High to Low)</option>
                      <option value="price-low">Price (Low to High)</option>
                      <option value="price-high">Price (High to Low)</option>
                    </select>
                  </div>
                </div>

                <p className="text-sm text-gray-600 mb-4">
                  Click ▶ to expand and view individual RFID-tagged items (EPCs) for each product. 
                  Stock counts are calculated from the number of unique EPCs.
                </p>
                <div className="overflow-auto max-h-[calc(110vh-500px)] border border-gray-200 rounded-lg mb-6">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-8"></th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Present</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Price (CHF)</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Restock At</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Optimal Level</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {products
                        .filter(product => {
                          // Search filter
                          if (productSearch) {
                            const search = productSearch.toLowerCase();
                            const matchesSearch = 
                              product.name.toLowerCase().includes(search) ||
                              product.sku.toLowerCase().includes(search) ||
                              product.category.toLowerCase().includes(search);
                            if (!matchesSearch) return false;
                          }
                          
                          // Category filter
                          if (productFilter === 'in-stock') {
                            return (product.current_stock || 0) > 0;
                          } else if (productFilter === 'low-stock') {
                            return product.reorder_threshold !== null && 
                                   (product.current_stock || 0) < product.reorder_threshold;
                          } else if (productFilter === 'out-of-stock') {
                            return (product.current_stock || 0) === 0;
                          } else if (productFilter === 'has-restock') {
                            return product.reorder_threshold !== null;
                          } else if (productFilter === 'no-restock') {
                            return product.reorder_threshold === null;
                          }
                          
                          return true;
                        })
                        .sort((a, b) => {
                          switch (productSort) {
                            case 'name':
                              return a.name.localeCompare(b.name);
                            case 'name-desc':
                              return b.name.localeCompare(a.name);
                            case 'sku':
                              return a.sku.localeCompare(b.sku);
                            case 'sku-desc':
                              return b.sku.localeCompare(a.sku);
                            case 'category':
                              return a.category.localeCompare(b.category);
                            case 'stock-low':
                              return (a.current_stock || 0) - (b.current_stock || 0);
                            case 'stock-high':
                              return (b.current_stock || 0) - (a.current_stock || 0);
                            case 'price-low':
                              return (a.unit_price || 0) - (b.unit_price || 0);
                            case 'price-high':
                              return (b.unit_price || 0) - (a.unit_price || 0);
                            default:
                              return 0;
                          }
                        })
                        .map((product) => {
                        const isExpanded = expandedProducts.has(product.id);
                        const items = productItems.get(product.id) || [];
                        
                        return (
                          <React.Fragment key={product.id}>
                            <tr className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-sm">
                                <button
                                  onClick={() => toggleProductExpand(product.id)}
                                  className="text-gray-500 hover:text-gray-700 transition-transform"
                                  style={{ transform: isExpanded ? 'rotate(90deg)' : 'none' }}
                                >
                                  ▶
                                </button>
                              </td>
                              <td className="px-4 py-3 text-sm font-mono">
                                <input
                                  type="text"
                                  defaultValue={product.sku}
                                  disabled={!editMode}
                                  onChange={(e) => editMode && trackProductChange(product.id, 'sku', e.target.value)}
                                  className={`w-full px-2 py-1 border rounded focus:outline-none focus:ring-1 focus:ring-[#0055A4] ${
                                    editMode ? 'border-gray-300 bg-white' : 'border-transparent bg-transparent cursor-default'
                                  }`}
                                />
                              </td>
                              <td className="px-4 py-3 text-sm">
                                <input
                                  type="text"
                                  defaultValue={product.name}
                                  disabled={!editMode}
                                  onChange={(e) => editMode && trackProductChange(product.id, 'name', e.target.value)}
                                  className={`w-full px-2 py-1 border rounded focus:outline-none focus:ring-1 focus:ring-[#0055A4] ${
                                    editMode ? 'border-gray-300 bg-white' : 'border-transparent bg-transparent cursor-default'
                                  }`}
                                />
                              </td>
                              <td className="px-4 py-3 text-sm">
                                <input
                                  type="text"
                                  defaultValue={product.category}
                                  disabled={!editMode}
                                  onChange={(e) => editMode && trackProductChange(product.id, 'category', e.target.value)}
                                  className={`w-full px-2 py-1 border rounded focus:outline-none focus:ring-1 focus:ring-[#0055A4] ${
                                    editMode ? 'border-gray-300 bg-white' : 'border-transparent bg-transparent cursor-default'
                                  }`}
                                />
                              </td>
                              <td className="px-4 py-3 text-sm text-center">
                                <span className={`font-medium ${
                                  product.reorder_threshold !== null && (product.current_stock || 0) < product.reorder_threshold 
                                    ? 'text-red-600' 
                                    : 'text-green-600'
                                }`}>
                                  {product.current_stock || 0}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-sm text-center text-gray-600">
                                {product.max_detected || 0}
                              </td>
                              <td className="px-4 py-3 text-sm">
                                <input
                                  type="number"
                                  step="0.01"
                                  defaultValue={product.unit_price}
                                  disabled={!editMode}
                                  onChange={(e) => editMode && trackProductChange(product.id, 'unit_price', parseFloat(e.target.value))}
                                  className={`w-20 px-2 py-1 border rounded focus:outline-none focus:ring-1 focus:ring-[#0055A4] ${
                                    editMode ? 'border-gray-300 bg-white' : 'border-transparent bg-transparent cursor-default'
                                  }`}
                                />
                              </td>
                              <td className="px-4 py-3 text-sm">
                                <input
                                  type="text"
                                  defaultValue={product.reorder_threshold ?? ''}
                                  disabled={!editMode}
                                  onChange={(e) => {
                                    if (editMode) {
                                      const val = e.target.value === '' ? null : parseInt(e.target.value);
                                      trackProductChange(product.id, 'reorder_threshold', val);
                                    }
                                  }}
                                  placeholder=""
                                  className={`w-20 px-2 py-1 border rounded focus:outline-none focus:ring-1 focus:ring-[#0055A4] ${
                                    editMode ? 'border-gray-300 bg-white' : 'border-transparent bg-transparent cursor-default'
                                  }`}
                                />
                              </td>
                              <td className="px-4 py-3 text-sm">
                                <input
                                  type="number"
                                  defaultValue={product.optimal_stock_level}
                                  disabled={!editMode}
                                  onChange={(e) => editMode && trackProductChange(product.id, 'optimal_stock_level', parseInt(e.target.value))}
                                  className={`w-16 px-2 py-1 border rounded focus:outline-none focus:ring-1 focus:ring-[#0055A4] ${
                                    editMode ? 'border-gray-300 bg-white' : 'border-transparent bg-transparent cursor-default'
                                  }`}
                                />
                              </td>
                            </tr>
                            
                            {isExpanded && (
                              <tr>
                                <td colSpan={9} className="px-4 py-2 bg-gray-50">
                                  <div className="pl-8">
                                    <h4 className="text-sm font-semibold text-gray-700 mb-2">
                                      Individual Items (EPCs) - {items.length} total
                                    </h4>
                                    {items.length === 0 ? (
                                      <p className="text-sm text-gray-500 italic">No items found for this product</p>
                                    ) : (
                                      <div className="max-h-60 overflow-y-auto">
                                        <table className="min-w-full text-sm">
                                          <thead className="bg-gray-100 sticky top-0">
                                            <tr>
                                              <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">RFID Tag (EPC)</th>
                                              <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Status</th>
                                              <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Position</th>
                                              <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Last Seen</th>
                                              <th className="px-3 py-2 text-left text-xs font-medium text-gray-600">Actions</th>
                                            </tr>
                                          </thead>
                                          <tbody className="divide-y divide-gray-200">
                                            {items.map((item) => (
                                              <tr key={item.id} className="hover:bg-gray-100">
                                                <td className="px-3 py-2 font-mono text-xs">{item.rfid_tag}</td>
                                                <td className="px-3 py-2">
                                                  <span className={`px-2 py-1 rounded-full text-xs ${
                                                    item.status === 'present' 
                                                      ? 'bg-green-100 text-green-800' 
                                                      : 'bg-gray-100 text-gray-800'
                                                  }`}>
                                                    {item.status}
                                                  </span>
                                                </td>
                                                <td className="px-3 py-2 text-gray-600">
                                                  {item.x_position && item.y_position 
                                                    ? `(${Math.round(item.x_position)}, ${Math.round(item.y_position)})` 
                                                    : 'N/A'}
                                                </td>
                                                <td className="px-3 py-2 text-gray-600">
                                                  {item.last_seen_at ? new Date(item.last_seen_at).toLocaleString() : 'Never'}
                                                </td>
                                                <td className="px-3 py-2">
                                                  <button
                                                    onClick={() => deleteItem(item.rfid_tag, product.id)}
                                                    disabled={loading}
                                                    className="text-red-600 hover:text-red-800 text-xs disabled:text-gray-400"
                                                  >
                                                    Delete
                                                  </button>
                                                </td>
                                              </tr>
                                            ))}
                                          </tbody>
                                        </table>
                                      </div>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Store Config Tab */}
            {activeTab === 'store' && storeConfig && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Store Configuration</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Store Width (cm)
                    </label>
                    <input
                      type="number"
                      defaultValue={storeConfig.store_width}
                      onChange={(e) => {
                        const newWidth = parseInt(e.target.value);
                        if (newWidth > 0) {
                          updateStoreConfig(newWidth, undefined, undefined);
                        }
                      }}
                      className="w-64 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Store Height (cm)
                    </label>
                    <input
                      type="number"
                      defaultValue={storeConfig.store_height}
                      onChange={(e) => {
                        const newHeight = parseInt(e.target.value);
                        if (newHeight > 0) {
                          updateStoreConfig(undefined, newHeight, undefined);
                        }
                      }}
                      className="w-64 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">
                      Current dimensions: {storeConfig.store_width} cm × {storeConfig.store_height} cm
                      ({(storeConfig.store_width / 100).toFixed(1)}m × {(storeConfig.store_height / 100).toFixed(1)}m)
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* System Info Tab */}
            {activeTab === 'system' && (
              <div>
                <h2 className="text-xl font-semibold mb-6">System Information</h2>
                
                <div className="space-y-6">
                  {/* Operating Status */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 uppercase mb-3">Operating Status</h3>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="p-4 bg-white border-2 border-gray-200 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Current Mode</p>
                        <p className={`text-2xl font-bold ${
                          mode?.mode === 'SIMULATION' ? 'text-blue-600' : 'text-green-600'
                        }`}>
                          {mode?.mode || 'N/A'}
                        </p>
                      </div>
                      <div className="p-4 bg-white border-2 border-gray-200 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Simulation Status</p>
                        <p className={`text-2xl font-bold ${
                          simulationStatus?.running ? 'text-green-600' : 'text-gray-400'
                        }`}>
                          {simulationStatus?.running ? 'Running' : 'Stopped'}
                        </p>
                        {simulationStatus?.pid && (
                          <p className="text-xs text-gray-500 mt-1">PID: {simulationStatus.pid}</p>
                        )}
                      </div>
                      <div className="p-4 bg-white border-2 border-gray-200 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Store Size</p>
                        <p className="text-2xl font-bold text-[#0055A4]">
                          {storeConfig ? `${(storeConfig.store_width / 100).toFixed(1)}m × ${(storeConfig.store_height / 100).toFixed(1)}m` : 'N/A'}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Inventory Overview */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 uppercase mb-3">Inventory Overview</h3>
                    <div className="grid grid-cols-4 gap-4">
                      <div className="p-4 bg-white border-2 border-gray-200 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Products</p>
                        <p className="text-2xl font-bold text-gray-900">{products.length}</p>
                        <p className="text-xs text-gray-500 mt-1">Unique SKUs</p>
                      </div>
                      <div className="p-4 bg-white border-2 border-gray-200 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Total Items</p>
                        <p className="text-2xl font-bold text-gray-900">
                          {products.reduce((sum, p) => sum + (p.max_detected || 0), 0)}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">All RFID tags</p>
                      </div>
                      <div className="p-4 bg-white border-2 border-green-200 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase font-semibold mb-1">In Stock</p>
                        <p className="text-2xl font-bold text-green-600">
                          {products.reduce((sum, p) => sum + (p.current_stock || 0), 0)}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">Present now</p>
                      </div>
                      <div className="p-4 bg-white border-2 border-red-200 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Needs Restock</p>
                        <p className="text-2xl font-bold text-red-600">
                          {products.filter(p => 
                            p.reorder_threshold !== null && (p.current_stock || 0) < p.reorder_threshold
                          ).length}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">Below threshold</p>
                      </div>
                    </div>
                  </div>

                  {/* Hardware Configuration */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 uppercase mb-3">Hardware Configuration</h3>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="p-4 bg-white border-2 border-gray-200 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase font-semibold mb-1">UWB Anchors</p>
                        <p className="text-2xl font-bold text-gray-900">{anchors.length}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {anchors.filter(a => a.is_active).length} active
                        </p>
                      </div>
                      <div className="p-4 bg-white border-2 border-gray-200 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Product Categories</p>
                        <p className="text-2xl font-bold text-gray-900">
                          {new Set(products.map(p => p.category)).size}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">Unique categories</p>
                      </div>
                      <div className="p-4 bg-white border-2 border-gray-200 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Total Inventory Value</p>
                        <p className="text-2xl font-bold text-gray-900">
                          ${products.reduce((sum, p) => sum + ((p.current_stock || 0) * (p.unit_price || 0)), 0).toFixed(0)}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">Current stock value</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
