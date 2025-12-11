import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface ProductVelocityChartProps {
  data: Array<{
    product_id: number;
    sku: string;
    name: string;
    velocity_daily: number;
    current_stock: number;
  }>;
}

export default function ProductVelocityChart({ data }: ProductVelocityChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        No velocity data available
      </div>
    );
  }

  // Take top 10 products by velocity
  const topProducts = data.slice(0, 10);

  // Transform data for chart
  const chartData = topProducts.map((p, index) => ({
    name: p.name.length > 20 ? p.name.substring(0, 20) + '...' : p.name,
    velocity: p.velocity_daily,
    stock: p.current_stock,
    index: index + 1
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 20, right: 30, left: 60, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="index" label={{ value: '', position: 'insideBottom', offset: -5 }} />
          <YAxis label={{ value: 'Velocity (units/day)', angle: -90, position: 'insideLeft' }} />
          <Tooltip 
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                return (
                  <div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
                    <p className="font-semibold">{payload[0].payload.name}</p>
                    <p className="text-sm text-blue-600">Velocity: {payload[0].value} units/day</p>
                    <p className="text-sm text-gray-600">Stock: {payload[0].payload.stock}</p>
                  </div>
                );
              }
              return null;
            }}
          />
          <Legend />
          <Line type="monotone" dataKey="velocity" stroke="#0055A4" strokeWidth={2} dot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
  );
}
