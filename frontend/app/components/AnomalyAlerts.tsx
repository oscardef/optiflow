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
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Anomaly Detection</h3>
        <div className="flex flex-col items-center justify-center py-8 text-gray-400">
          <span className="text-4xl mb-2">✓</span>
          <p>No anomalies detected</p>
          <p className="text-sm">All products behaving normally</p>
        </div>
      </div>
    );
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-50 border-red-300 text-red-800';
      case 'medium':
        return 'bg-yellow-50 border-yellow-300 text-yellow-800';
      default:
        return 'bg-blue-50 border-blue-300 text-blue-800';
    }
  };

  const getAnomalyIcon = (type: string) => {
    return type === 'spike' ? '📈' : '📉';
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Anomaly Detection</h3>
        <span className="bg-purple-100 text-purple-700 px-3 py-1 rounded-full text-sm font-medium">
          {data.count} detected
        </span>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {data.anomalies.map((anomaly) => (
          <div
            key={anomaly.product_id}
            className={`border-2 rounded-lg p-4 ${getSeverityColor(anomaly.severity)}`}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center">
                <span className="text-2xl mr-3">{getAnomalyIcon(anomaly.anomaly_type)}</span>
                <div>
                  <h4 className="font-semibold text-sm">{anomaly.name}</h4>
                  <p className="text-xs opacity-75">SKU: {anomaly.sku}</p>
                </div>
              </div>
              <span className="text-xs font-bold uppercase px-2 py-1 rounded bg-white bg-opacity-50">
                {anomaly.severity}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 mt-3 text-xs">
              <div>
                <p className="opacity-75">Type</p>
                <p className="font-semibold capitalize">{anomaly.anomaly_type}</p>
              </div>
              <div>
                <p className="opacity-75">Recent Sales</p>
                <p className="font-semibold">{anomaly.recent_sales}</p>
              </div>
              <div>
                <p className="opacity-75">Expected</p>
                <p className="font-semibold">{anomaly.expected_sales.toFixed(1)}</p>
              </div>
            </div>

            <div className="mt-2 pt-2 border-t border-current border-opacity-20">
              <p className="text-xs opacity-75">
                Z-Score: <span className="font-bold">{anomaly.z_score.toFixed(2)}</span>
                {anomaly.anomaly_type === 'spike' && ' (Unusual increase in sales)'}
                {anomaly.anomaly_type === 'drop' && ' (Unusual decrease in sales)'}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
