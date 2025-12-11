import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface TurnoverRateChartProps {
  data: Array<{
    product_id: number;
    name: string;
    category: string;
    turnover_rate: number;
    velocity_daily: number;
  }>;
}

export default function TurnoverRateChart({ data }: TurnoverRateChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        No turnover data available
      </div>
    );
  }

  // Get top 10 products by turnover rate
  const topTurnover = [...data]
    .sort((a, b) => b.turnover_rate - a.turnover_rate)
    .slice(0, 10)
    .map(p => ({
      name: p.name.length > 25 ? p.name.substring(0, 25) + '...' : p.name,
      turnover: p.turnover_rate,
      category: p.category
    }));

  // Color based on turnover rate
  const getColor = (rate: number) => {
    if (rate > 1) return '#10B981'; // High turnover - green
    if (rate > 0.5) return '#F59E0B'; // Medium turnover - orange
    return '#EF4444'; // Low turnover - red
  };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={topTurnover} layout="vertical" margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" label={{ value: 'Turnover Rate', position: 'insideBottom', offset: -5 }} />
        <YAxis 
          type="category" 
          dataKey="name" 
          width={200}
        />
        <Tooltip 
          formatter={(value: any) => [value.toFixed(2), 'Turnover Rate']}
          labelFormatter={(label) => `Product: ${label}`}
        />
        <Bar dataKey="turnover" radius={[0, 4, 4, 0]}>
          {topTurnover.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={getColor(entry.turnover)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
