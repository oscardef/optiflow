import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell } from 'recharts';

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

interface ProductInsightsProps {
  data: ProductData[];
}

export default function ProductInsights({ data }: ProductInsightsProps) {
  if (!data || data.length === 0) {
    return <div className="bg-white border-l-4 border-gray-400 p-4">No product data</div>;
  }

  // Calculate key metrics
  const totalProducts = data.length;
  const criticalStock = data.filter(p => p.days_until_stockout !== null && p.days_until_stockout < 7).length;
  const deadStock = data.filter(p => p.velocity_daily < 0.1 && p.current_stock > 20).length;
  const topPerformers = data.filter(p => p.velocity_daily > 1).length;
  const avgVelocity = data.reduce((sum, p) => sum + (p.velocity_daily || 0), 0) / totalProducts;
  const avgTurnover = data.reduce((sum, p) => sum + (p.turnover_rate || 0), 0) / totalProducts;

  // Get top 10 by velocity
  const topProducts = [...data].sort((a, b) => (b.velocity_daily || 0) - (a.velocity_daily || 0)).slice(0, 10);

  // Get urgent restocks
  const urgentRestocks = [...data]
    .filter(p => p.days_until_stockout !== null && p.days_until_stockout < 7)
    .sort((a, b) => (a.days_until_stockout || 999) - (b.days_until_stockout || 999))
    .slice(0, 5);

  // Chart data for top products
  const chartData = topProducts.map(p => ({
    name: p.name.length > 20 ? p.name.substring(0, 18) + '..' : p.name,
    velocity: p.velocity_daily,
    stock: p.current_stock
  }));

  return (
    <div className="bg-white border-l-4 border-blue-600 h-full flex flex-col">
      {/* Header with Key Metrics */}
      <div className="bg-gray-50 border-b border-gray-200 p-4">
        <h2 className="text-lg font-bold text-gray-900 mb-3">Inventory Performance Overview</h2>
        <div className="grid grid-cols-5 gap-3 text-xs">
          <div>
            <div className="text-gray-600 uppercase tracking-wide mb-1">Total Products</div>
            <div className="text-2xl font-bold text-gray-900">{totalProducts}</div>
          </div>
          <div>
            <div className="text-gray-600 uppercase tracking-wide mb-1">Critical Stock</div>
            <div className="text-2xl font-bold text-red-600">{criticalStock}</div>
            <div className="text-xs text-gray-500">&lt;7 days left</div>
          </div>
          <div>
            <div className="text-gray-600 uppercase tracking-wide mb-1">Dead Stock</div>
            <div className="text-2xl font-bold text-orange-600">{deadStock}</div>
            <div className="text-xs text-gray-500">slow movers</div>
          </div>
          <div>
            <div className="text-gray-600 uppercase tracking-wide mb-1">Top Performers</div>
            <div className="text-2xl font-bold text-green-600">{topPerformers}</div>
            <div className="text-xs text-gray-500">&gt;1 unit/day</div>
          </div>
          <div>
            <div className="text-gray-600 uppercase tracking-wide mb-1">Avg Velocity</div>
            <div className="text-2xl font-bold text-blue-600">{avgVelocity.toFixed(2)}</div>
            <div className="text-xs text-gray-500">units/day</div>
          </div>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-2 gap-4 p-4 min-h-0">
        {/* Top Velocity Chart */}
        <div className="border border-gray-200 flex flex-col">
          <div className="bg-gray-100 px-3 py-2 border-b border-gray-300">
            <h3 className="text-sm font-bold text-gray-900">Top 10 Products by Sales Velocity</h3>
          </div>
          <div className="flex-1 p-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="horizontal" margin={{ top: 5, right: 10, left: 10, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis 
                  type="category" 
                  dataKey="name" 
                  angle={-45}
                  textAnchor="end"
                  height={80}
                  tick={{ fontSize: 9 }}
                />
                <YAxis 
                  type="number"
                  label={{ value: 'Units/Day', angle: -90, position: 'insideLeft', style: { fontSize: 10 } }}
                  tick={{ fontSize: 9 }}
                />
                <Bar dataKey="velocity" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index < 3 ? '#10b981' : index < 7 ? '#3b82f6' : '#6b7280'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Urgent Restocks Table */}
        <div className="border border-gray-200 flex flex-col overflow-hidden">
          <div className="bg-red-600 text-white px-3 py-2 flex items-baseline justify-between">
            <h3 className="text-sm font-bold">⚠ Urgent Restock Required</h3>
            <span className="text-xs font-medium">{urgentRestocks.length} Product{urgentRestocks.length !== 1 ? 's' : ''}</span>
          </div>
          {urgentRestocks.length > 0 ? (
            <div className="flex-1 overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="bg-gray-100 sticky top-0">
                  <tr className="border-b border-gray-300">
                    <th className="text-left px-2 py-2 font-bold text-gray-900">Product</th>
                    <th className="text-right px-2 py-2 font-bold text-gray-900">Stock</th>
                    <th className="text-right px-2 py-2 font-bold text-gray-900">Days Left</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {urgentRestocks.map((product) => (
                    <tr key={product.product_id} className="hover:bg-gray-50">
                      <td className="px-2 py-2">
                        <div className="font-medium text-gray-900">{product.name}</div>
                        <div className="text-gray-500">{product.category}</div>
                      </td>
                      <td className="px-2 py-2 text-right font-bold">{product.current_stock}</td>
                      <td className="px-2 py-2 text-right">
                        <span className={`inline-block px-2 py-1 font-bold text-white ${
                          (product.days_until_stockout || 999) < 3 ? 'bg-red-600' :
                          (product.days_until_stockout || 999) < 5 ? 'bg-orange-600' :
                          'bg-yellow-600'
                        }`}>
                          {product.days_until_stockout}d
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500 text-xs">
              No urgent restocks needed
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
