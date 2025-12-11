import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface CategoryStockValueProps {
  data: Array<{
    category: string;
    product_count: number;
    total_stock: number;
    sales_30_days: number;
    total_revenue: number;
    avg_velocity: number;
  }>;
}

const COLORS = ['#0055A4', '#003d7a', '#4A90E2', '#7AB8FF', '#A8D0FF', '#E3F2FD', '#BBDEFB'];

export default function CategoryStockValue({ data }: CategoryStockValueProps) {
  if (!data || data.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        No category data available
      </div>
    );
  }

  const chartData = data
    .map(item => ({
      category: item.category.length > 12 ? item.category.substring(0, 10) + '..' : item.category,
      fullCategory: item.category,
      revenue: Number(item.total_revenue.toFixed(2)),
      sales: item.sales_30_days
    }))
    .sort((a, b) => b.revenue - a.revenue);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart 
        data={chartData} 
        margin={{ top: 10, right: 20, left: 15, bottom: 10 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
        <XAxis 
          dataKey="category" 
          angle={-45}
          textAnchor="end"
          height={80}
          interval={0}
          tick={{ fontSize: 12 }}
        />
        <YAxis 
          tick={{ fontSize: 12 }}
          label={{ 
            value: 'Revenue (CHF)', 
            angle: -90, 
            position: 'insideLeft',
            offset: 10
          }} 
        />
        <Tooltip 
          contentStyle={{ backgroundColor: 'white', border: '1px solid #ccc', borderRadius: '4px' }}
          formatter={(value: any, name: string) => {
            if (name === 'revenue') return [`${value} CHF`, 'Revenue'];
            return [value, name];
          }}
          labelFormatter={(label) => {
            const item = chartData.find(d => d.category === label);
            return item ? item.fullCategory : label;
          }}
        />
        <Bar dataKey="revenue" radius={[4, 4, 0, 0]} maxBarSize={60}>
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
