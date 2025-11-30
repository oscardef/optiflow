'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import AnalyticsOverview from '../components/AnalyticsOverview';
import ProductVelocityChart from '../components/ProductVelocityChart';
import TopProductsTable from '../components/TopProductsTable';
import CategoryDonut from '../components/CategoryDonut';
import AIClusterView from '../components/AIClusterView';
import DemandForecastChart from '../components/DemandForecastChart';
import AnomalyAlerts from '../components/AnomalyAlerts';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface BackfillStatus {
  running: boolean;
  message: string;
  records: number;
}

type TabType = 'kpis' | 'overview' | 'products' | 'ai-insights';

export default function AnalyticsPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabType>('kpis');
  const [loading, setLoading] = useState(true);
  const [analyticsOverview, setAnalyticsOverview] = useState<any>(null);
  const [productVelocity, setProductVelocity] = useState<any[]>([]);
  const [topProducts, setTopProducts] = useState<any[]>([]);
  const [categoryPerformance, setCategoryPerformance] = useState<any[]>([]);
  const [aiClusters, setAiClusters] = useState<any>(null);
  const [anomalies, setAnomalies] = useState<any>(null);
  const [selectedProductForForecast, setSelectedProductForForecast] = useState<number | null>(null);
  const [demandForecast, setDemandForecast] = useState<any>(null);

  // Backfill controls
  const [showBackfill, setShowBackfill] = useState(false);
  const [backfillDensity, setBackfillDensity] = useState('normal');
  const [backfillDays, setBackfillDays] = useState(30);
  const [backfillStatus, setBackfillStatus] = useState<BackfillStatus | null>(null);
  const [isBackfilling, setIsBackfilling] = useState(false);

  const fetchAnalyticsData = async () => {
    try {
      const [overview, velocity, top, category, clusters, anomaliesData] = await Promise.all([
        fetch(`${API_URL}/analytics/overview?days=30`).then(r => r.ok ? r.json() : null),
        fetch(`${API_URL}/analytics/product-velocity?days=7`).then(r => r.ok ? r.json() : []),
        fetch(`${API_URL}/analytics/top-products?limit=20&metric=sales`).then(r => r.ok ? r.json() : []),
        fetch(`${API_URL}/analytics/category-performance?days=30`).then(r => r.ok ? r.json() : []),
        fetch(`${API_URL}/analytics/ai/clusters?n_clusters=4`).then(r => r.ok ? r.json() : null),
        fetch(`${API_URL}/analytics/ai/anomalies?days=7`).then(r => r.ok ? r.json() : null),
      ]);

      setAnalyticsOverview(overview);
      setProductVelocity(velocity || []);
      setTopProducts(top || []);
      setCategoryPerformance(category || []);
      setAiClusters(clusters);
      setAnomalies(anomaliesData);

      // Auto-select first product for forecast if available
      if (top && top.length > 0 && !selectedProductForForecast) {
        setSelectedProductForForecast(top[0].product_id);
      }
    } catch (error) {
      console.error('Error fetching analytics:', error);
      setAnalyticsOverview(null);
      setProductVelocity([]);
      setTopProducts([]);
      setCategoryPerformance([]);
      setAiClusters(null);
      setAnomalies(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchDemandForecast = async (productId: number) => {
    try {
      const forecast = await fetch(`${API_URL}/analytics/ai/forecast/${productId}?days=7`).then(r => r.json());
      setDemandForecast(forecast);
    } catch (error) {
      console.error('Error fetching forecast:', error);
    }
  };

  const triggerBackfill = async () => {
    setIsBackfilling(true);
    try {
      const response = await fetch(`${API_URL}/analytics/backfill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          density: backfillDensity,
          days: backfillDays
        })
      });
      
      const result = await response.json();
      setBackfillStatus(result);
      
      if (result.status === 'success') {
        // Refresh analytics data after backfill
        setTimeout(() => {
          fetchAnalyticsData();
        }, 1000);
      }
    } catch (error) {
      console.error('Error triggering backfill:', error);
      setBackfillStatus({
        running: false,
        message: 'Failed to trigger backfill',
        records: 0
      });
    } finally {
      setIsBackfilling(false);
    }
  };

  useEffect(() => {
    fetchAnalyticsData();
    const interval = setInterval(fetchAnalyticsData, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedProductForForecast) {
      fetchDemandForecast(selectedProductForForecast);
    }
  }, [selectedProductForForecast]);

  if (loading) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600 text-xl">Loading analytics...</div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-50 flex flex-col overflow-hidden">
      <div className="flex-shrink-0 px-6 pt-6 pb-4">
        {/* Header */}
        <div className="max-w-7xl mx-auto mb-4 flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>
            <p className="text-gray-600 mt-1">AI-powered insights and performance metrics</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowBackfill(!showBackfill)}
              className="px-4 py-2 text-sm font-medium text-white bg-[#0055A4] hover:bg-[#003d7a] rounded-lg transition-colors"
            >
              {showBackfill ? 'Hide' : 'Generate Data'}
            </button>
            <button
              onClick={() => router.push('/')}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-[#0055A4] hover:bg-gray-50 border border-gray-300 rounded-lg transition-colors flex items-center gap-2"
            >
              ← Back to Dashboard
            </button>
          </div>
        </div>

        {/* Backfill Controls */}
        {showBackfill && (
          <div className="max-w-7xl mx-auto mb-4 bg-white rounded-lg shadow p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Generate Historical Data</h3>
            <div className="grid grid-cols-4 gap-4 items-end">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Density
                </label>
                <select
                  value={backfillDensity}
                  onChange={(e) => setBackfillDensity(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0055A4] focus:border-[#0055A4]"
                  disabled={isBackfilling}
                >
                  <option value="sparse">Sparse (few events)</option>
                  <option value="normal">Normal</option>
                  <option value="dense">Dense</option>
                  <option value="extreme">Extreme (max events)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Days
                </label>
                <input
                  type="number"
                  value={backfillDays}
                  onChange={(e) => setBackfillDays(parseInt(e.target.value) || 30)}
                  min="1"
                  max="365"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0055A4] focus:border-[#0055A4]"
                  disabled={isBackfilling}
                />
              </div>
              <div>
                <button
                  onClick={triggerBackfill}
                  disabled={isBackfilling}
                  className="w-full px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:bg-gray-400 rounded-lg transition-colors"
                >
                  {isBackfilling ? 'Generating...' : 'Generate'}
                </button>
              </div>
              <div>
                {backfillStatus && (
                  <div className={`text-sm ${backfillStatus.running ? 'text-blue-600' : backfillStatus.records > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {backfillStatus.message}
                    {backfillStatus.records > 0 && ` (${backfillStatus.records} records)`}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Main Content Area with Tabs */}
      <div className="flex-1 px-6 pb-6 overflow-hidden">
        <div className="max-w-7xl mx-auto h-full flex flex-col">
          <div className="bg-white rounded-lg shadow h-full flex flex-col overflow-hidden">
            {/* Tab Navigation */}
            <div className="flex-shrink-0 border-b border-gray-200">
              <nav className="flex -mb-px">
                {[
                  { id: 'kpis', label: 'KPIs' },
                  { id: 'overview', label: 'Performance' },
                  { id: 'products', label: 'Products' },
                  { id: 'ai-insights', label: 'AI Insights' },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as TabType)}
                    className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === tab.id
                        ? 'border-[#0055A4] text-[#0055A4]'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </nav>
            </div>

            {/* Tab Content */}
            <div className="flex-1 p-6 overflow-auto">
              {/* KPIs Tab */}
              {activeTab === 'kpis' && (
                <div className="h-full">
                  <AnalyticsOverview data={analyticsOverview} />
                </div>
              )}

              {/* Performance Overview Tab */}
              {activeTab === 'overview' && (
                <div className="h-full grid grid-cols-2 gap-6">
                  <div className="bg-gray-50 rounded-lg p-4 flex flex-col min-h-0">
                    <h3 className="text-base font-semibold text-gray-900 mb-3">Product Velocity (7 Days)</h3>
                    <div className="flex-1 min-h-0">
                      <ProductVelocityChart data={productVelocity} />
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4 flex flex-col min-h-0">
                    <h3 className="text-base font-semibold text-gray-900 mb-3">Category Distribution</h3>
                    <div className="flex-1 min-h-0">
                      <CategoryDonut data={categoryPerformance} />
                    </div>
                  </div>
                </div>
              )}

              {/* Product Analysis Tab */}
              {activeTab === 'products' && (
                <div className="h-full">
                  <TopProductsTable data={topProducts} />
                </div>
              )}

              {/* AI Insights Tab */}
              {activeTab === 'ai-insights' && (
                <div className="h-full flex flex-col gap-4 overflow-auto">
                  {/* Anomaly Alerts - Compact */}
                  <div className="flex-shrink-0">
                    <AnomalyAlerts data={anomalies} />
                  </div>

                  {/* AI Analysis - Two Columns */}
                  <div className="flex-1 grid grid-cols-2 gap-4 min-h-0">
                    <div className="bg-gray-50 rounded-lg p-4 flex flex-col min-h-0">
                      <h3 className="text-base font-semibold text-gray-900 mb-2">Product Clusters</h3>
                      <p className="text-xs text-gray-600 mb-3">K-means grouping by velocity & stock</p>
                      <div className="flex-1 min-h-0">
                        <AIClusterView data={aiClusters} />
                      </div>
                    </div>

                    <div className="bg-gray-50 rounded-lg p-4 flex flex-col min-h-0">
                      <h3 className="text-base font-semibold text-gray-900 mb-2">Demand Forecast</h3>
                      <select
                        value={selectedProductForForecast || ''}
                        onChange={(e) => setSelectedProductForForecast(Number(e.target.value))}
                        className="mb-3 px-3 py-1.5 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-[#0055A4] focus:border-transparent"
                      >
                        <option value="">Select product...</option>
                        {topProducts.slice(0, 10).map(p => (
                          <option key={p.product_id} value={p.product_id}>
                            {p.name}
                          </option>
                        ))}
                      </select>
                      <div className="flex-1 min-h-0">
                        {demandForecast && selectedProductForForecast ? (
                          <DemandForecastChart
                            productId={selectedProductForForecast}
                            productName={topProducts.find(p => p.product_id === selectedProductForForecast)?.name || ''}
                            data={demandForecast}
                          />
                        ) : (
                          <div className="h-full flex items-center justify-center text-gray-400 text-sm">
                            Select a product to view forecast
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
