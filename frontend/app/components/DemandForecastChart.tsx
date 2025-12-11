import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend } from 'recharts';

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
      <div className="h-full flex flex-col items-center justify-center border border-gray-300 bg-gray-50 p-6">
        <div className="text-4xl mb-3">📈</div>
        <div className="text-sm font-medium text-gray-700 mb-1">7-Day Sales Forecast</div>
        <p className="text-xs text-gray-500 text-center">Select a product to view AI prediction</p>
      </div>
    );
  }

  const chartData = data.forecast.map((value, index) => ({
    day: index + 1,
    forecast: value,
    average: data.average_daily_sales
  }));

  const totalPredicted = data.forecast.reduce((a, b) => a + b, 0);
  const trend = data.forecast[6] > data.forecast[0] ? 'increasing' : data.forecast[6] < data.forecast[0] ? 'decreasing' : 'stable';

  return (
    <div className="h-full flex flex-col border border-gray-300 bg-white">
      <div className="bg-blue-600 text-white px-3 py-2">
        <div className="text-xs font-bold uppercase">AI Sales Forecast</div>
        <div className="text-xs mt-1 truncate opacity-90">{productName}</div>
      </div>

      <div className="flex-1 p-3">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey="day" 
              tick={{ fontSize: 10 }}
              label={{ value: 'Day', position: 'insideBottom', offset: -5, style: { fontSize: 10, fontWeight: 'bold' } }}
            />
            <YAxis 
              tick={{ fontSize: 10 }}
              label={{ 
                value: 'Units', 
                angle: -90, 
                position: 'insideLeft',
                style: { fontSize: 10, fontWeight: 'bold' }
              }} 
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'white', 
                border: '2px solid #2563eb',
                padding: '6px',
                fontSize: '11px'
              }}
              formatter={(value: any) => [`${value.toFixed(1)} units`, 'Predicted']}
              labelFormatter={(label) => `Day ${label}`}
            />
            <Legend wrapperStyle={{ fontSize: '10px' }} />
            <ReferenceLine 
              y={data.average_daily_sales} 
              stroke="#9ca3af" 
              strokeDasharray="5 5"
              label={{ value: 'Historical Avg', position: 'right', style: { fontSize: 9, fill: '#6b7280' } }}
            />
            <Line 
              type="monotone" 
              dataKey="forecast" 
              stroke="#2563eb" 
              strokeWidth={2}
              dot={{ fill: '#2563eb', r: 3 }}
              activeDot={{ r: 5 }}
              name="Forecast"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="border-t border-gray-200 bg-gray-50">
        <div className="grid grid-cols-3 divide-x divide-gray-300">
          <div className="px-3 py-2 text-center">
            <div className="text-xs text-gray-600 uppercase mb-1">7-Day Total</div>
            <div className="text-lg font-bold text-blue-600">{totalPredicted.toFixed(0)}</div>
          </div>
          <div className="px-3 py-2 text-center">
            <div className="text-xs text-gray-600 uppercase mb-1">Daily Avg</div>
            <div className="text-lg font-bold text-gray-900">{data.average_daily_sales.toFixed(1)}</div>
          </div>
          <div className="px-3 py-2 text-center">
            <div className="text-xs text-gray-600 uppercase mb-1">Trend</div>
            <div className={`text-sm font-bold ${
              trend === 'increasing' ? 'text-green-600' : trend === 'decreasing' ? 'text-red-600' : 'text-gray-600'
            }`}>
              {trend === 'increasing' && '↗ Rising'}
              {trend === 'decreasing' && '↘ Falling'}
              {trend === 'stable' && '→ Stable'}
            </div>
          </div>
        </div>
      </div>

      <div className={`px-3 py-2 text-xs border-t-2 ${
        data.confidence === 'high' ? 'bg-green-50 border-green-600 text-green-900' :
        data.confidence === 'medium' ? 'bg-yellow-50 border-yellow-600 text-yellow-900' :
        'bg-red-50 border-red-600 text-red-900'
      }`}>
        <div className="font-bold uppercase mb-1">
          {data.confidence === 'high' && '✓ High Confidence'}
          {data.confidence === 'medium' && '⚠ Medium Confidence'}
          {data.confidence === 'low' && '⚠ Low Confidence'}
        </div>
        <div>
          {data.confidence === 'high' && 'Strong historical data available'}
          {data.confidence === 'medium' && 'Moderate data - use as guidance'}
          {data.confidence === 'low' && 'Limited data - prediction less reliable'}
        </div>
      </div>
    </div>
  );
}
