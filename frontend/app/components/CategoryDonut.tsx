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
      <div className="h-full flex items-center justify-center text-gray-400">
        No category data available
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
    <ResponsiveContainer width="100%" height="100%">
        <PieChart margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
          <Pie
            data={chartData}
            cx="50%"
            cy="45%"
            innerRadius={50}
            outerRadius={90}
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
                    <p className="text-sm text-green-600">Revenue: {data.revenue.toFixed(2)} CHF</p>
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
  );
}
