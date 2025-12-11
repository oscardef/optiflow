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
      <div className="bg-white border border-gray-300 p-4">
        <div className="flex items-center justify-between mb-3 pb-3 border-b border-gray-900">
          <h3 className="text-sm font-bold text-gray-900 uppercase">Anomaly Detection</h3>
          <span className="text-xs text-gray-600">NO ALERTS</span>
        </div>
        <p className="text-xs text-gray-600">All products operating within normal parameters</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-300 p-4">
      <div className="flex items-center justify-between mb-3 pb-3 border-b border-gray-900">
        <h3 className="text-sm font-bold text-gray-900 uppercase">Anomaly Detection</h3>
        <span className="bg-black text-white px-2 py-1 text-xs font-bold">{data.count}</span>
      </div>

      <div className="space-y-2 max-h-80 overflow-y-auto">
        {data.anomalies.map((anomaly) => (
          <div
            key={anomaly.product_id}
            className="border border-gray-300 bg-gray-50 p-3"
          >
            <div className="flex items-start justify-between mb-2 pb-2 border-b border-gray-300">
              <div className="flex-1">
                <div className="text-xs font-bold text-gray-900">{anomaly.name}</div>
                <div className="text-xs text-gray-600 mt-0.5">{anomaly.sku}</div>
              </div>
              <div className={`text-xs font-bold uppercase px-2 py-0.5 ml-2 ${
                anomaly.severity === 'high' ? 'bg-black text-white' : 
                anomaly.severity === 'medium' ? 'bg-gray-400 text-white' : 
                'bg-gray-200 text-gray-900'
              }`}>
                {anomaly.severity}
              </div>
            </div>

            <div className="grid grid-cols-4 gap-2 text-xs">
              <div>
                <div className="text-gray-600 mb-0.5">TYPE</div>
                <div className="font-bold uppercase">{anomaly.anomaly_type}</div>
              </div>
              <div>
                <div className="text-gray-600 mb-0.5">RECENT</div>
                <div className="font-bold">{anomaly.recent_sales}</div>
              </div>
              <div>
                <div className="text-gray-600 mb-0.5">EXPECTED</div>
                <div className="font-bold">{anomaly.expected_sales.toFixed(1)}</div>
              </div>
              <div>
                <div className="text-gray-600 mb-0.5">Z-SCORE</div>
                <div className="font-bold">{anomaly.z_score.toFixed(2)}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
