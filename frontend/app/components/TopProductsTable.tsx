'use client';

import React, { useState } from 'react';
import InfoTooltip from './InfoTooltip';

// Simple refresh icon component
const RefreshIcon = ({ className = '' }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

interface ProductVelocityData {
  product_id: number;
  sku: string;
  name: string;
  category: string;
  current_stock: number;
  velocity_daily: number;
  turnover_rate: number;
  days_until_stockout: number | null;
}

interface TopProductsTableProps {
  data: ProductVelocityData[];
  onRefresh?: () => Promise<void>;
  isLoading?: boolean;
  error?: string | null;
}

export default function TopProductsTable({ 
  data, 
  onRefresh, 
  isLoading = false, 
  error = null 
}: TopProductsTableProps) {
  const [sortBy, setSortBy] = useState<'velocity' | 'stock' | 'turnover'>('velocity');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    if (!onRefresh || isRefreshing) return;
    
    setIsRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setIsRefreshing(false);
    }
  };

  // Error State
  if (error && !isLoading) {
    return (
      <div className="h-full flex flex-col">
        <div className="mb-4 flex justify-between items-start">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 tracking-tight">Product Velocity Analysis</h2>
            <p className="text-sm text-gray-600">Top 20 products by daily movement rate</p>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center border border-red-200 rounded-lg bg-red-50">
          <div className="text-center max-w-md px-4">
            <div className="text-red-600 font-medium mb-2">Failed to load product data</div>
            <p className="text-gray-600 text-sm mb-4">{error}</p>
            {onRefresh && (
              <button
                onClick={handleRefresh}
                disabled={isRefreshing}
                className="px-4 py-2 text-sm font-medium text-white bg-gray-900 hover:bg-gray-800 disabled:bg-gray-400 rounded-lg transition-colors"
              >
                {isRefreshing ? 'Retrying...' : 'Retry'}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Loading State
  if (isLoading) {
    return (
      <div className="h-full flex flex-col">
        <div className="mb-4 flex justify-between items-start">
          <div>
            <div className="h-6 w-56 bg-gray-200 rounded animate-pulse mb-2"></div>
            <div className="h-4 w-72 bg-gray-100 rounded animate-pulse"></div>
          </div>
          <div className="h-9 w-24 bg-gray-200 rounded animate-pulse"></div>
        </div>
        <div className="flex-1 border border-gray-200 rounded-lg overflow-hidden">
          <div className="h-12 bg-gray-50 border-b border-gray-200"></div>
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-14 border-b border-gray-100 flex items-center px-4 gap-4">
              <div className="h-4 w-20 bg-gray-100 rounded animate-pulse"></div>
              <div className="h-4 flex-1 bg-gray-100 rounded animate-pulse"></div>
              <div className="h-4 w-24 bg-gray-100 rounded animate-pulse"></div>
              <div className="h-4 w-16 bg-gray-100 rounded animate-pulse"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Empty State
  if (!data || data.length === 0) {
    return (
      <div className="h-full flex flex-col">
        <div className="mb-4 flex justify-between items-start">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 tracking-tight">Product Velocity Analysis</h2>
            <p className="text-sm text-gray-600">Top 20 products by daily movement rate</p>
          </div>
          {onRefresh && (
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 hover:border-gray-400 disabled:bg-gray-100 rounded-lg transition-colors"
            >
              <RefreshIcon className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          )}
        </div>
        <div className="flex-1 flex items-center justify-center border border-gray-200 rounded-lg bg-gray-50">
          <div className="text-center">
            <p className="text-gray-500 font-medium mb-2">No product data available</p>
            <p className="text-gray-400 text-sm">Try refreshing or check if the simulation is running</p>
          </div>
        </div>
      </div>
    );
  }

  const handleSort = (column: 'velocity' | 'stock' | 'turnover') => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const sortedData = [...data].sort((a, b) => {
    let aVal = 0, bVal = 0;
    if (sortBy === 'velocity') {
      aVal = a.velocity_daily ?? 0;
      bVal = b.velocity_daily ?? 0;
    } else if (sortBy === 'stock') {
      aVal = a.current_stock ?? 0;
      bVal = b.current_stock ?? 0;
    } else {
      aVal = a.turnover_rate ?? 0;
      bVal = b.turnover_rate ?? 0;
    }
    return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
  });

  return (
    <div className="h-full flex flex-col">
      <div className="mb-4 flex justify-between items-start">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 tracking-tight">Product Velocity Analysis</h2>
          <p className="text-sm text-gray-600">Top 20 products by daily movement rate</p>
        </div>
        {onRefresh && (
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 hover:border-gray-400 disabled:bg-gray-100 rounded-lg transition-colors"
          >
            <RefreshIcon className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        )}
      </div>

      <div className="flex-1 border border-gray-200 rounded-lg overflow-hidden">
        <div className="overflow-auto h-full">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50 sticky top-0">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <div className="flex items-center gap-1">
                  SKU
                  <InfoTooltip content="Stock Keeping Unit - Unique product identifier" />
                </div>
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Product Name
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Category
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('stock')}
              >
                <div className="flex items-center gap-1">
                  Stock {sortBy === 'stock' && (sortOrder === 'asc' ? '↑' : '↓')}
                  <InfoTooltip content="Current inventory count - units available in stock" />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('velocity')}
              >
                <div className="flex items-center gap-1">
                  Velocity {sortBy === 'velocity' && (sortOrder === 'asc' ? '↑' : '↓')}
                  <InfoTooltip content="Daily sales rate - units sold per day on average" />
                </div>
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('turnover')}
              >
                <div className="flex items-center gap-1">
                  Turnover {sortBy === 'turnover' && (sortOrder === 'asc' ? '↑' : '↓')}
                  <InfoTooltip content="Inventory turnover rate - sales relative to current inventory" />
                </div>
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <div className="flex items-center gap-1">
                  Days to Stockout
                  <InfoTooltip content="Estimated days until stock runs out at current velocity" />
                </div>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedData.slice(0, 20).map((product) => (
              <tr key={product.product_id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                  {product.sku || 'N/A'}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                  {product.name || 'Unknown'}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                  {product.category || 'N/A'}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700 font-medium">
                  {product.current_stock ?? 0}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm font-semibold text-gray-900">
                  {product.velocity_daily != null ? product.velocity_daily.toFixed(2) : '0.00'}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                  {product.turnover_rate != null ? product.turnover_rate.toFixed(2) : '0.00'}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm">
                  {product.days_until_stockout != null && product.days_until_stockout > 0 ? (
                    <span className={product.days_until_stockout < 7 ? 'text-red-600 font-semibold' : 'text-gray-700'}>
                      {product.days_until_stockout.toFixed(0)} days
                    </span>
                  ) : (
                    <span className="text-gray-400">N/A</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
