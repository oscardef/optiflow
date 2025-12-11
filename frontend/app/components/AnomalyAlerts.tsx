import React from 'react';

interface Anomaly {
  product_id: number;
  sku: string;
  name: string;
  anomaly_type: string;
  severity: string;
  z_score: number;
  recent_sales: number;
  expected_sales: number;
}

interface AnomalyAlertsProps {
  data: {
    anomalies: Anomaly[];
    count: number;
  } | null;
}

export default function AnomalyAlerts({ data }: AnomalyAlertsProps) {
  if (!data || !data.anomalies || data.anomalies.length === 0) {
    return (
      <div className="bg-white border-l-4 border-green-600 p-4">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-bold text-gray-900">Sales Pattern Analysis</h2>
          <span className="text-xs font-medium text-green-600 uppercase">All Normal</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border-l-4 border-red-600">
      <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-bold text-gray-900">⚠ Sales Anomalies Detected</h2>
          <span className="text-sm font-bold text-red-600">{data.count} Product{data.count > 1 ? 's' : ''}</span>
        </div>
        <p className="text-xs text-gray-600 mt-1">Products with unusual sales patterns requiring investigation</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-gray-100 border-b border-gray-300">
            <tr>
              <th className="text-left px-3 py-2 font-bold text-gray-900 uppercase tracking-wide">Product</th>
              <th className="text-center px-2 py-2 font-bold text-gray-900 uppercase tracking-wide">Pattern</th>
              <th className="text-right px-2 py-2 font-bold text-gray-900 uppercase tracking-wide">Recent</th>
              <th className="text-right px-2 py-2 font-bold text-gray-900 uppercase tracking-wide">Expected</th>
              <th className="text-right px-2 py-2 font-bold text-gray-900 uppercase tracking-wide">Deviation</th>
              <th className="text-left px-3 py-2 font-bold text-gray-900 uppercase tracking-wide">Impact</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {data.anomalies.map((anomaly) => {
              const difference = anomaly.recent_sales - anomaly.expected_sales;
              const percentChange = ((difference / anomaly.expected_sales) * 100);
              const isSpike = anomaly.anomaly_type === 'spike';
              
              return (
                <tr key={anomaly.product_id} className={`hover:bg-gray-50 ${
                  anomaly.severity === 'high' ? 'bg-red-50' : anomaly.severity === 'medium' ? 'bg-yellow-50' : ''
                }`}>
                  <td className="px-3 py-3">
                    <div className="font-bold text-gray-900">{anomaly.name}</div>
                    <div className="text-gray-500 mt-0.5">{anomaly.sku}</div>
                  </td>
                  <td className="px-2 py-3 text-center">
                    <span className={`inline-block px-2 py-1 font-bold text-white ${
                      isSpike ? 'bg-red-600' : 'bg-orange-600'
                    }`}>
                      {isSpike ? '↑ SURGE' : '↓ DROP'}
                    </span>
                  </td>
                  <td className="px-2 py-3 text-right font-bold">{anomaly.recent_sales}</td>
                  <td className="px-2 py-3 text-right text-gray-600">{anomaly.expected_sales.toFixed(0)}</td>
                  <td className="px-2 py-3 text-right">
                    <div className={`font-bold ${isSpike ? 'text-red-600' : 'text-orange-600'}`}>
                      {difference > 0 ? '+' : ''}{difference}
                    </div>
                    <div className="text-gray-500">({percentChange > 0 ? '+' : ''}{percentChange.toFixed(0)}%)</div>
                  </td>
                  <td className="px-3 py-3">
                    <div className={`text-xs ${anomaly.severity === 'high' ? 'text-red-600' : anomaly.severity === 'medium' ? 'text-yellow-600' : 'text-blue-600'}`}>
                      {anomaly.severity === 'high' && 'Critical - Investigate immediately'}
                      {anomaly.severity === 'medium' && 'Monitor - Check within 24h'}
                      {anomaly.severity === 'low' && 'Note - Minor variation'}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
