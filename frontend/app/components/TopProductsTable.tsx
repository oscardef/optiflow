import React, { useState } from 'react';

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
}

export default function TopProductsTable({ data }: TopProductsTableProps) {
  const [sortBy, setSortBy] = useState<'velocity' | 'stock' | 'turnover'>('velocity');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Product Velocity Table</h3>
        <div className="text-center text-gray-400 py-8">No data available</div>
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
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Product Velocity Analysis</h3>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                SKU
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Product Name
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Category
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('stock')}
              >
                Stock {sortBy === 'stock' && (sortOrder === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('velocity')}
              >
                Velocity {sortBy === 'velocity' && (sortOrder === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('turnover')}
              >
                Turnover {sortBy === 'turnover' && (sortOrder === 'asc' ? '↑' : '↓')}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Days to Stockout
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedData.slice(0, 20).map((product) => (
              <tr key={product.product_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                  {product.sku || 'N/A'}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                  {product.name || 'Unknown'}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                  {product.category || 'N/A'}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                  {product.current_stock ?? 0}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm font-semibold text-blue-600">
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
  );
}
