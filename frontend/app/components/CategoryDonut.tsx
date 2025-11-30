import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface CategoryPerformance {
  category: string;
  product_count: number;
  total_stock: number;
  sales_30_days: number;
  total_revenue: number;
}

interface CategoryDonutProps {
  data: CategoryPerformance[];
}

const COLORS = ['#0055A4', '#00A3E0', '#FF6B35', '#4ECDC4', '#95E1D3', '#F38181'];

export default function CategoryDonut({ data }: CategoryDonutProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Category Performance</h3>
        <div className="h-64 flex items-center justify-center text-gray-400">
          No category data available
        </div>
      </div>
    );
  }

  const chartData = data.map(cat => ({
    name: cat.category,
    value: cat.sales_30_days,
    revenue: cat.total_revenue,
    stock: cat.total_stock,
    products: cat.product_count
  }));

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Sales by Category (30 Days)</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            fill="#8884d8"
            paddingAngle={2}
            dataKey="value"
            label={({ name, percent }) => `${name} ${percent ? (percent * 100).toFixed(0) : 0}%`}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip 
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
                    <p className="font-semibold">{data.name}</p>
                    <p className="text-sm text-blue-600">Sales: {data.value}</p>
                    <p className="text-sm text-green-600">Revenue: ${data.revenue.toFixed(2)}</p>
                    <p className="text-sm text-gray-600">Products: {data.products}</p>
                    <p className="text-sm text-gray-600">Stock: {data.stock}</p>
                  </div>
                );
              }
              return null;
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
        {data.map((cat, index) => (
          <div key={cat.category} className="flex items-center">
            <div 
              className="w-3 h-3 rounded-full mr-2" 
              style={{ backgroundColor: COLORS[index % COLORS.length] }}
            />
            <span className="text-gray-700">{cat.category}: <span className="font-semibold">{cat.sales_30_days}</span></span>
          </div>
        ))}
      </div>
    </div>
  );
}
