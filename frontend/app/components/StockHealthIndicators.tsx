import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface StockHealthProps {
  overview: {
    low_stock_items: number;
    stockout_risk_items: number;
    dead_stock_count: number;
    total_products: number;
  } | null;
}

export default function StockHealthIndicators({ overview }: StockHealthProps) {
  if (!overview) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        No stock health data available
      </div>
    );
  }

  const healthyStock = Math.max(
    0,
    overview.total_products - 
    overview.low_stock_items - 
    overview.stockout_risk_items - 
    overview.dead_stock_count
  );

  const data = [
    { name: 'Healthy Stock', value: healthyStock, color: '#10B981' },
    { name: 'Low Stock', value: overview.low_stock_items, color: '#F59E0B' },
    { name: 'Stockout Risk', value: overview.stockout_risk_items, color: '#EF4444' },
    { name: 'Dead Stock', value: overview.dead_stock_count, color: '#6B7280' },
  ].filter(item => item.value > 0);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
        <Pie
          data={data}
          cx="50%"
          cy="45%"
          labelLine={false}
          label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
          outerRadius={70}
          fill="#8884d8"
          dataKey="value"
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip formatter={(value: any) => [`${value} products`, 'Count']} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
