'use client';

import React, { useState, useMemo } from 'react';

interface ProductData {
  product_id: number;
  sku: string;
  name: string;
  category: string;
  current_stock: number;
  velocity_daily: number;
  turnover_rate: number;
  days_until_stockout: number | null;
}

interface ProductAnalyticsProps {
  data: ProductData[];
  onRefresh?: () => Promise<void>;
  isLoading?: boolean;
}

export default function ProductAnalytics({ data, onRefresh, isLoading }: ProductAnalyticsProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [stockFilter, setStockFilter] = useState<'all' | 'healthy' | 'low' | 'critical'>('all');
  const [velocityFilter, setVelocityFilter] = useState<'all' | 'fast' | 'medium' | 'slow'>('all');
  const [sortBy, setSortBy] = useState<'name' | 'stock' | 'velocity' | 'stockout'>('velocity');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Get unique categories
  const categories = useMemo(() => {
    const cats = new Set(data.map(p => p.category));
    return Array.from(cats).sort();
  }, [data]);

  // Calculate summary metrics
  const summary = useMemo(() => {
    const fastMovers = data.filter(p => (p.velocity_daily || 0) > 5).length;
    const slowMovers = data.filter(p => (p.velocity_daily || 0) < 1).length;
    const stockoutAlerts = data.filter(p => p.days_until_stockout !== null && p.days_until_stockout < 7).length;
    const deadStock = data.filter(p => (p.velocity_daily || 0) < 0.5 && (p.current_stock || 0) > 20).length;
    
    return { fastMovers, slowMovers, stockoutAlerts, deadStock };
  }, [data]);

  // Filter and sort data
  const filteredData = useMemo(() => {
    let filtered = data;

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(p =>
        p.name.toLowerCase().includes(query) ||
        p.sku.toLowerCase().includes(query) ||
        p.category.toLowerCase().includes(query)
      );
    }

    // Category filter
    if (selectedCategories.length > 0) {
      filtered = filtered.filter(p => selectedCategories.includes(p.category));
    }

    // Stock status filter
    if (stockFilter !== 'all') {
      filtered = filtered.filter(p => {
        const stock = p.current_stock || 0;
        const daysUntilStockout = p.days_until_stockout;
        
        if (stockFilter === 'critical') {
          return stock < 10 || (daysUntilStockout !== null && daysUntilStockout < 7);
        } else if (stockFilter === 'low') {
          return stock >= 10 && stock < 30 && (daysUntilStockout === null || daysUntilStockout >= 7);
        } else if (stockFilter === 'healthy') {
          return stock >= 30;
        }
        return true;
      });
    }

    // Velocity filter
    if (velocityFilter !== 'all') {
      filtered = filtered.filter(p => {
        const velocity = p.velocity_daily || 0;
        if (velocityFilter === 'fast') return velocity > 3;
        if (velocityFilter === 'medium') return velocity >= 1 && velocity <= 3;
        if (velocityFilter === 'slow') return velocity < 1;
        return true;
      });
    }

    // Sort
    filtered.sort((a, b) => {
      let aVal = 0, bVal = 0;
      
      if (sortBy === 'name') {
        return sortOrder === 'asc' 
          ? a.name.localeCompare(b.name)
          : b.name.localeCompare(a.name);
      } else if (sortBy === 'stock') {
        aVal = a.current_stock || 0;
        bVal = b.current_stock || 0;
      } else if (sortBy === 'velocity') {
        aVal = a.velocity_daily || 0;
        bVal = b.velocity_daily || 0;
      } else if (sortBy === 'stockout') {
        aVal = a.days_until_stockout !== null ? a.days_until_stockout : 999;
        bVal = b.days_until_stockout !== null ? b.days_until_stockout : 999;
      }
      
      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
    });

    return filtered;
  }, [data, searchQuery, selectedCategories, stockFilter, velocityFilter, sortBy, sortOrder]);

  const toggleCategory = (category: string) => {
    setSelectedCategories(prev =>
      prev.includes(category)
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  };

  const getStockStatus = (stock: number, daysUntilStockout: number | null) => {
    if (stock < 10 || (daysUntilStockout !== null && daysUntilStockout < 7)) {
      return { label: 'Critical', color: 'bg-red-500', textColor: 'text-red-700', bgColor: 'bg-red-50' };
    } else if (stock < 30) {
      return { label: 'Low', color: 'bg-yellow-500', textColor: 'text-yellow-700', bgColor: 'bg-yellow-50' };
    } else {
      return { label: 'Healthy', color: 'bg-green-500', textColor: 'text-green-700', bgColor: 'bg-green-50' };
    }
  };

  const getVelocityIndicator = (velocity: number) => {
    if (velocity > 3) return { icon: '↑', color: 'text-green-600', label: 'Fast' };
    if (velocity >= 1) return { icon: '→', color: 'text-blue-600', label: 'Medium' };
    return { icon: '↓', color: 'text-red-600', label: 'Slow' };
  };

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-gray-600">Loading product analytics...</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <div className="text-2xl font-bold text-green-700">{summary.fastMovers}</div>
          <div className="text-xs text-green-600 font-medium">Fast Movers</div>
          <div className="text-xs text-gray-600">&gt; 5 units/day</div>
        </div>
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
          <div className="text-2xl font-bold text-orange-700">{summary.slowMovers}</div>
          <div className="text-xs text-orange-600 font-medium">Slow Movers</div>
          <div className="text-xs text-gray-600">&lt; 1 unit/day</div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <div className="text-2xl font-bold text-red-700">{summary.stockoutAlerts}</div>
          <div className="text-xs text-red-600 font-medium">Stockout Alerts</div>
          <div className="text-xs text-gray-600">&lt; 7 days remaining</div>
        </div>
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
          <div className="text-2xl font-bold text-purple-700">{summary.deadStock}</div>
          <div className="text-xs text-purple-600 font-medium">Dead Stock Risk</div>
          <div className="text-xs text-gray-600">Low velocity, high stock</div>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="mb-4 space-y-3">
        <input
          type="text"
          placeholder="Search by product name, SKU, or category..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
        />
        
        <div className="flex items-center gap-4 flex-wrap">
          {/* Category filters */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-600">Categories:</span>
            <div className="flex gap-1 flex-wrap">
              {categories.map(cat => (
                <button
                  key={cat}
                  onClick={() => toggleCategory(cat)}
                  className={`px-2 py-1 text-xs rounded-full transition-colors ${
                    selectedCategories.includes(cat)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Stock status filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-600">Stock:</span>
            {(['all', 'critical', 'low', 'healthy'] as const).map(filter => (
              <button
                key={filter}
                onClick={() => setStockFilter(filter)}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  stockFilter === filter
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {filter.charAt(0).toUpperCase() + filter.slice(1)}
              </button>
            ))}
          </div>

          {/* Velocity filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-600">Velocity:</span>
            {(['all', 'fast', 'medium', 'slow'] as const).map(filter => (
              <button
                key={filter}
                onClick={() => setVelocityFilter(filter)}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  velocityFilter === filter
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {filter.charAt(0).toUpperCase() + filter.slice(1)}
              </button>
            ))}
          </div>

          <div className="ml-auto text-xs text-gray-600">
            Showing {filteredData.length} of {data.length} products
          </div>
        </div>
      </div>

      {/* Products Table */}
      <div className="flex-1 border border-gray-200 rounded-lg overflow-hidden flex flex-col min-h-0">
        {/* Table Header */}
        <div className="bg-gray-50 border-b border-gray-200 px-4 py-3 grid grid-cols-12 gap-4 text-xs font-medium text-gray-600">
          <div className="col-span-3 cursor-pointer hover:text-gray-900" onClick={() => {
            setSortBy('name');
            setSortOrder(sortBy === 'name' && sortOrder === 'asc' ? 'desc' : 'asc');
          }}>
            Product {sortBy === 'name' && (sortOrder === 'asc' ? '↑' : '↓')}
          </div>
          <div className="col-span-2">Category</div>
          <div className="col-span-2 cursor-pointer hover:text-gray-900" onClick={() => {
            setSortBy('stock');
            setSortOrder(sortBy === 'stock' && sortOrder === 'asc' ? 'desc' : 'asc');
          }}>
            Stock Level {sortBy === 'stock' && (sortOrder === 'asc' ? '↑' : '↓')}
          </div>
          <div className="col-span-2 cursor-pointer hover:text-gray-900" onClick={() => {
            setSortBy('velocity');
            setSortOrder(sortBy === 'velocity' && sortOrder === 'asc' ? 'desc' : 'asc');
          }}>
            Velocity {sortBy === 'velocity' && (sortOrder === 'asc' ? '↑' : '↓')}
          </div>
          <div className="col-span-2 cursor-pointer hover:text-gray-900" onClick={() => {
            setSortBy('stockout');
            setSortOrder(sortBy === 'stockout' && sortOrder === 'asc' ? 'desc' : 'asc');
          }}>
            Days Until Stockout {sortBy === 'stockout' && (sortOrder === 'asc' ? '↑' : '↓')}
          </div>
          <div className="col-span-1">Status</div>
        </div>

        {/* Table Body */}
        <div className="flex-1 overflow-y-auto">
          {filteredData.length > 0 ? (
            filteredData.map((product, idx) => {
              const stockStatus = getStockStatus(product.current_stock || 0, product.days_until_stockout);
              const velocityInd = getVelocityIndicator(product.velocity_daily || 0);
              const stockPercentage = Math.min(100, ((product.current_stock || 0) / 50) * 100);

              return (
                <div
                  key={product.product_id}
                  className={`px-4 py-3 grid grid-cols-12 gap-4 items-center text-sm border-b border-gray-100 hover:bg-gray-50 ${
                    idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                  }`}
                >
                  <div className="col-span-3">
                    <div className="font-medium text-gray-900 truncate">{product.name}</div>
                    <div className="text-xs text-gray-500">{product.sku}</div>
                  </div>
                  <div className="col-span-2">
                    <span className="inline-block px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded">
                      {product.category}
                    </span>
                  </div>
                  <div className="col-span-2">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{product.current_stock}</span>
                      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${stockStatus.color}`}
                          style={{ width: `${stockPercentage}%` }}
                        />
                      </div>
                    </div>
                  </div>
                  <div className="col-span-2">
                    <div className="flex items-center gap-1">
                      <span className={`text-lg ${velocityInd.color}`}>{velocityInd.icon}</span>
                      <span className="font-medium">{product.velocity_daily.toFixed(1)}</span>
                      <span className="text-xs text-gray-500">/day</span>
                    </div>
                  </div>
                  <div className="col-span-2">
                    {product.days_until_stockout !== null ? (
                      <span className={`font-medium ${
                        product.days_until_stockout < 7 ? 'text-red-600' :
                        product.days_until_stockout < 14 ? 'text-orange-600' :
                        'text-gray-700'
                      }`}>
                        {product.days_until_stockout} days
                      </span>
                    ) : (
                      <span className="text-gray-400 text-xs">N/A</span>
                    )}
                  </div>
                  <div className="col-span-1">
                    <span className={`inline-block w-2 h-2 rounded-full ${stockStatus.color}`}></span>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              No products match your filters
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
