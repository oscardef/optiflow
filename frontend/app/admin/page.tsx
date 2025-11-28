'use client';

import React, { useState, useEffect } from 'react';
import type { Anchor, Product, StoreConfig, ModeResponse, SimulationStatus, AnchorValidation, ConfigMode } from '@/src/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

  const switchMode = async (newMode: ConfigMode) => {
    if (!confirm(`Switch to ${newMode} mode? All data will be preserved and can be resumed by switching back.`)) {
      return;
    }

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
      showMessage('error', 'Failed to switch mode');
    } finally {
      setLoading(false);
    }
  };

  const startSimulation = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/simulation/start`, { method: 'POST' });
      const data = await res.json();
      
      if (res.ok && data.success) {
        showMessage('success', 'Simulation started successfully');
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

  const updateStoreConfig = async (width: number, height: number) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/config/store`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ store_width: width, store_height: height })
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

  return (
    <div className="min-h-screen bg-gray-50 p-6">
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
                      ? 'border-blue-500 text-blue-600'
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
              <div className="space-y-6">
                <div>
                  <h2 className="text-xl font-semibold mb-4">Operating Mode</h2>
                  <div className="flex items-center gap-4 mb-6">
                    <span className="text-gray-700">Current Mode:</span>
                    <span className={`px-4 py-2 rounded-full font-semibold ${
                      mode?.mode === 'SIMULATION' 
                        ? 'bg-purple-100 text-purple-800' 
                        : 'bg-green-100 text-green-800'
                    }`}>
                      {mode?.mode || 'Loading...'}
                    </span>
                  </div>

                  <div className="flex gap-4">
                    <button
                      onClick={() => switchMode('SIMULATION')}
                      disabled={mode?.mode === 'SIMULATION' || loading}
                      className="px-6 py-3 bg-[#0055A4] text-white rounded-lg hover:bg-[#003d7a] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                    >
                      Switch to Simulation
                    </button>
                    <button
                      onClick={() => switchMode('REAL')}
                      disabled={mode?.mode === 'REAL' || loading}
                      className="px-6 py-3 bg-[#0055A4] text-white rounded-lg hover:bg-[#003d7a] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                    >
                      Switch to Real
                    </button>
                  </div>
                </div>

                {mode?.mode === 'REAL' && (
                  <div className="border-t pt-6">
                    <h2 className="text-xl font-semibold mb-4">Anchor Validation</h2>
                    <button
                      onClick={validateAnchors}
                      disabled={loading}
                      className="px-6 py-3 bg-[#0055A4] text-white rounded-lg hover:bg-[#003d7a] disabled:bg-gray-300 transition-colors mb-4"
                    >
                      Validate Anchors
                    </button>

                    {validation && (
                      <div className={`p-4 rounded-lg ${
                        validation.valid ? 'bg-green-50 border border-green-200' : 'bg-yellow-50 border border-yellow-200'
                      }`}>
                        <p className="font-medium mb-2">{validation.message}</p>
                        {validation.warnings.length > 0 && (
                          <ul className="list-disc list-inside space-y-1 text-sm">
                            {validation.warnings.map((warning, i) => (
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
                <h2 className="text-xl font-semibold mb-4">Anchor Management</h2>
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
                      {anchors.map((anchor) => (
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
                          <td className="px-4 py-3 text-sm">
                            <button
                              onClick={() => deleteAnchor(anchor.id)}
                              className="text-red-600 hover:text-red-800"
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
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
                    className={`px-6 py-2 text-white rounded-lg transition-colors ${
                      editMode 
                        ? 'bg-green-600 hover:bg-green-700' 
                        : 'bg-[#0055A4] hover:bg-[#003d7a]'
                    } disabled:bg-gray-300 disabled:cursor-not-allowed`}
                  >
                    {editMode ? `Save Changes ${changedProducts.size > 0 ? `(${changedProducts.size})` : ''}` : 'Edit Products'}
                  </button>
                </div>
                <p className="text-sm text-gray-600 mb-4">
                  Click ▶ to expand and view individual RFID-tagged items (EPCs) for each product. 
                  Stock counts are calculated from the number of unique EPCs.
                </p>
                <div className="overflow-auto max-h-[600px] border border-gray-200 rounded-lg">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-8"></th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Present</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Price ($)</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Restock At</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Optimal Level</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {products.map((product) => {
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
                                  defaultValue={product.reorder_threshold ?? 'None'}
                                  disabled={!editMode}
                                  onChange={(e) => {
                                    if (editMode) {
                                      const val = e.target.value.toLowerCase() === 'none' || e.target.value === '' ? null : parseInt(e.target.value);
                                      trackProductChange(product.id, 'reorder_threshold', val);
                                    }
                                  }}
                                  placeholder="None"
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
                          updateStoreConfig(newWidth, storeConfig.store_height);
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
                          updateStoreConfig(storeConfig.store_width, newHeight);
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
                <h2 className="text-xl font-semibold mb-4">System Information</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-purple-50 rounded-lg">
                    <p className="text-sm text-gray-600 mb-1">Current Mode</p>
                    <p className="text-2xl font-bold text-purple-600">{mode?.mode || 'N/A'}</p>
                  </div>
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <p className="text-sm text-gray-600 mb-1">Simulation Status</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {simulationStatus?.running ? 'Running' : 'Stopped'}
                    </p>
                  </div>
                  <div className="p-4 bg-green-50 rounded-lg">
                    <p className="text-sm text-gray-600 mb-1">Configured Anchors</p>
                    <p className="text-2xl font-bold text-green-600">{anchors.length}</p>
                  </div>
                  <div className="p-4 bg-yellow-50 rounded-lg">
                    <p className="text-sm text-gray-600 mb-1">Total Products</p>
                    <p className="text-2xl font-bold text-yellow-600">{products.length}</p>
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
