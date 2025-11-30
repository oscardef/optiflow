import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

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
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Demand Forecast</h3>
        <div className="h-64 flex items-center justify-center text-gray-400">
          Select a product to view forecast
        </div>
      </div>
    );
  }

  // Generate chart data
  const chartData = data.forecast.map((value, index) => ({
    day: `Day ${index + 1}`,
    forecast: value,
    upper_bound: value + (data.historical_variance * 0.5),
    lower_bound: Math.max(0, value - (data.historical_variance * 0.5))
  }));

  const confidenceColor = {
    high: 'text-green-600',
    medium: 'text-yellow-600',
    low: 'text-red-600'
  }[data.confidence] || 'text-gray-600';

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold">7-Day Demand Forecast</h3>
          <p className="text-sm text-gray-600 mt-1">{productName}</p>
        </div>
        <div className="text-right">
          <span className="text-sm text-purple-600 font-medium">AI Prediction</span>
          <p className={`text-xs ${confidenceColor} font-semibold mt-1`}>
            {data.confidence.toUpperCase()} confidence
          </p>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="day" />
          <YAxis label={{ value: 'Expected Sales', angle: -90, position: 'insideLeft' }} />
          <Tooltip 
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                return (
                  <div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
                    <p className="font-semibold">{payload[0].payload.day}</p>
                    <p className="text-sm text-purple-600">Forecast: {payload[0].value?.toFixed(1)} units</p>
                    <p className="text-sm text-gray-500">Range: {payload[0].payload.lower_bound.toFixed(1)} - {payload[0].payload.upper_bound.toFixed(1)}</p>
                  </div>
                );
              }
              return null;
            }}
          />
          <Legend />
          <Area 
            type="monotone" 
            dataKey="upper_bound" 
            stackId="1"
            stroke="none" 
            fill="#DDD6FE" 
            fillOpacity={0.3}
            name="Uncertainty Band"
          />
          <Area 
            type="monotone" 
            dataKey="forecast" 
            stackId="2"
            stroke="#8B5CF6" 
            fill="#8B5CF6" 
            fillOpacity={0.6}
            strokeWidth={2}
            name="Predicted Sales"
          />
        </AreaChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
        <div className="bg-purple-50 p-3 rounded">
          <p className="text-xs text-gray-600">Avg Daily Sales</p>
          <p className="text-lg font-semibold text-purple-700">{data.average_daily_sales.toFixed(1)}</p>
        </div>
        <div className="bg-purple-50 p-3 rounded">
          <p className="text-xs text-gray-600">7-Day Total</p>
          <p className="text-lg font-semibold text-purple-700">
            {data.forecast.reduce((a, b) => a + b, 0).toFixed(0)}
          </p>
        </div>
        <div className="bg-purple-50 p-3 rounded">
          <p className="text-xs text-gray-600">Variance</p>
          <p className="text-lg font-semibold text-purple-700">{data.historical_variance.toFixed(1)}</p>
        </div>
      </div>
    </div>
  );
}
