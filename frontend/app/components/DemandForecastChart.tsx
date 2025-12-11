import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface DemandForecastChartProps {
  productId: number;
  productName: string;
  data: {
    forecast: number[];
    average_daily_sales: number;
    confidence: string;
    historical_variance: number;
  } | null;
}

export default function DemandForecastChart({ productId, productName, data }: DemandForecastChartProps) {
  if (!data || !data.forecast || data.forecast.length === 0) {
    return (
      <div className="h-full flex items-center justify-center border border-gray-300 bg-gray-50">
        <p className="text-xs text-gray-600">SELECT PRODUCT</p>
      </div>
    );
  }

  const chartData = data.forecast.map((value, index) => ({
    day: index + 1,
    forecast: value
  }));

  return (
    <div className="h-full flex flex-col border border-gray-300 bg-white">
      <div className="p-2 border-b border-gray-900 bg-black text-white">
        <div className="text-xs font-bold">7-DAY FORECAST</div>
        <div className="text-xs mt-0.5 truncate">{productName}</div>
      </div>

      <div className="flex-1 min-h-0 p-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" />
            <XAxis 
              dataKey="day" 
              tick={{ fontSize: 10 }}
              label={{ value: 'DAY', position: 'insideBottom', offset: -5, style: { fontSize: 10, fontWeight: 'bold' } }}
            />
            <YAxis 
              tick={{ fontSize: 10 }}
              label={{ 
                value: 'UNITS', 
                angle: -90, 
                position: 'insideLeft',
                style: { fontSize: 10, fontWeight: 'bold' }
              }} 
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'white', 
                border: '1px solid black',
                padding: '4px 8px'
              }}
              labelStyle={{ fontSize: 10, fontWeight: 'bold' }}
              itemStyle={{ fontSize: 10 }}
              formatter={(value: any) => [`${value.toFixed(1)} units`, 'FORECAST']}
              labelFormatter={(label) => `DAY ${label}`}
            />
            <Line 
              type="monotone" 
              dataKey="forecast" 
              stroke="#000000" 
              strokeWidth={2}
              dot={{ fill: '#000000', r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="border-t border-gray-900 p-2 grid grid-cols-3 gap-2 bg-gray-50">
        <div className="text-center">
          <div className="text-xs text-gray-600">AVG DAILY</div>
          <div className="text-sm font-bold">{data.average_daily_sales.toFixed(1)}</div>
        </div>
        <div className="text-center border-x border-gray-300">
          <div className="text-xs text-gray-600">CONFIDENCE</div>
          <div className="text-sm font-bold uppercase">{data.confidence}</div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-600">VARIANCE</div>
          <div className="text-sm font-bold">{data.historical_variance.toFixed(1)}</div>
        </div>
      </div>
    </div>
  );
}
