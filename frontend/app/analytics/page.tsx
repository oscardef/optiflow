'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import AnalyticsOverview from '../components/AnalyticsOverview';
import ProductVelocityChart from '../components/ProductVelocityChart';
import TopProductsTable from '../components/TopProductsTable';
import CategoryDonut from '../components/CategoryDonut';
import ProductInsights from '../components/ProductInsights';
import ProductAnalytics from '../components/ProductAnalytics';
import DemandForecastChart from '../components/DemandForecastChart';
import AnomalyAlerts from '../components/AnomalyAlerts';
import SalesTimeSeriesChart from '../components/SalesTimeSeriesChart';

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

interface BackfillStatus {
  running: boolean;
  message: string;
  records: number;
  progress?: number;
  total?: number;
}

interface SetupStatus {
  products: number;
  stock_levels: number;
  inventory_items: number;
  purchase_events: number;
  stock_snapshots: number;
  setup_complete: boolean;
  has_analytics_data: boolean;
}

type TabType = 'kpis' | 'overview' | 'products' | 'ai-insights';

export default function AnalyticsPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabType>('kpis');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analyticsOverview, setAnalyticsOverview] = useState<any>(null);
  const [productVelocity, setProductVelocity] = useState<any[]>([]);
  const [topProducts, setTopProducts] = useState<any[]>([]);
  const [categoryPerformance, setCategoryPerformance] = useState<any[]>([]);
  const [aiClusters, setAiClusters] = useState<any>(null);
  const [anomalies, setAnomalies] = useState<any>(null);
  const [selectedProductForForecast, setSelectedProductForForecast] = useState<number | null>(null);
  const [demandForecast, setDemandForecast] = useState<any>(null);
  const [salesTimeSeries, setSalesTimeSeries] = useState<any[]>([]);

  // Date range and interval controls
  const [dateRange, setDateRange] = useState<'7' | '30' | '90' | 'custom'>('30');
  const [timeInterval, setTimeInterval] = useState<'hour' | 'day' | 'week' | 'month'>('day');
  const [customStartDate, setCustomStartDate] = useState<string>('');
  const [customEndDate, setCustomEndDate] = useState<string>('');
  
  // Applied values (what's actually being displayed)
  const [appliedInterval, setAppliedInterval] = useState<'hour' | 'day' | 'week' | 'month'>('day');

  // Helper to get date range for API calls
  const getDateParams = () => {
    if (dateRange === 'custom' && customStartDate && customEndDate) {
      return `start_date=${customStartDate}&end_date=${customEndDate}`;
    }
    return `days=${dateRange}`;
  };

  // Backfill controls
  const [showBackfill, setShowBackfill] = useState(false);
  const [backfillDensity, setBackfillDensity] = useState('normal');
  const [backfillDays, setBackfillDays] = useState(30);
  const [backfillStatus, setBackfillStatus] = useState<BackfillStatus | null>(null);
  const [isBackfilling, setIsBackfilling] = useState(false);
  const [setupStatus, setSetupStatus] = useState<SetupStatus | null>(null);

  const fetchSetupStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/setup/status`);
      const status = await response.json();
      setSetupStatus(status);
    } catch (error) {
      console.error('Error fetching setup status:', error);
    }
  };

  const fetchAnalyticsData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Apply the current selections
      setAppliedInterval(timeInterval);
      
      const dateParams = getDateParams();
      const [overview, velocity, top, category, clusters, anomaliesData, timeSeries] = await Promise.all([
        fetch(`${API_URL}/analytics/overview?${dateParams}&interval=${timeInterval}`).then(r => r.ok ? r.json() : null),
        fetch(`${API_URL}/analytics/product-velocity?${dateParams}&interval=${timeInterval}`).then(r => r.ok ? r.json() : []),
        fetch(`${API_URL}/analytics/top-products?limit=20&metric=sales&${dateParams}&interval=${timeInterval}`).then(r => r.ok ? r.json() : []),
        fetch(`${API_URL}/analytics/category-performance?${dateParams}&interval=${timeInterval}`).then(r => r.ok ? r.json() : []),
        fetch(`${API_URL}/analytics/ai/clusters?n_clusters=4`).then(r => r.ok ? r.json() : null),
        fetch(`${API_URL}/analytics/ai/anomalies?${dateParams}`).then(r => r.ok ? r.json() : null),
        fetch(`${API_URL}/analytics/sales-time-series?${dateParams}&interval=${timeInterval}`).then(r => r.ok ? r.json() : []),
      ]);

      setAnalyticsOverview(overview);
      setProductVelocity(velocity || []);
      setTopProducts(top || []);
      setCategoryPerformance(category || []);
      setAiClusters(clusters);
      setAnomalies(anomaliesData);
      setSalesTimeSeries(timeSeries || []);

      // Auto-select first product for forecast if available
      if (top && top.length > 0 && !selectedProductForForecast) {
        setSelectedProductForForecast(top[0].product_id);
      }
    } catch (err) {
      console.error('Error fetching analytics:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch analytics data');
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
      const response = await fetch(`${API_URL}/analytics/ai/forecast/${productId}?days=7`);
      if (response.ok) {
        const forecast = await response.json();
        setDemandForecast(forecast);
      } else {
        console.error('Forecast not available:', response.status);
        setDemandForecast(null);
      }
    } catch (error) {
      console.error('Error fetching forecast:', error);
      setDemandForecast(null);
    }
  };

  const clearData = async () => {
    if (!confirm('This will delete all purchase events and stock snapshots (but keeps products and items). Are you sure?')) {
      return;
    }
    
    setIsBackfilling(true);
    try {
      const response = await fetch(`${API_URL}/analytics/clear`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const result = await response.json();
      setBackfillStatus({
        running: false,
        message: result.message || 'Data cleared successfully',
        records: 0
      });
      
      // Refresh status and analytics
      setTimeout(() => {
        fetchSetupStatus();
        fetchAnalyticsData();
      }, 1000);
    } catch (error) {
      console.error('Error clearing data:', error);
      setBackfillStatus({
        running: false,
        message: 'Failed to clear data',
        records: 0
      });
    } finally {
      setIsBackfilling(false);
    }
  };

  const triggerBackfill = async () => {
    setIsBackfilling(true);
    try {
      // First, verify and fix any setup issues
      const setupResponse = await fetch(`${API_URL}/setup/verify-and-fix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const setupResult = await setupResponse.json();
      
      // Check if there are critical issues (no products)
      const noProductsIssue = setupResult.issues?.find((i: any) => i.issue === 'no_products');
      if (noProductsIssue) {
        setBackfillStatus({
          running: false,
          message: 'No products found. Please run product generation first: docker compose exec backend bash -c "cd /simulation && python generate_inventory.py --items 100"',
          records: 0
        });
        return;
      }
      
      // Run backfill
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
      
      // Start polling for progress if backfill is running
      if (result.status === 'running' || result.running) {
        pollBackfillStatus();
      } else if (result.status === 'success') {
        // Refresh setup status and analytics data after backfill
        setTimeout(() => {
          fetchSetupStatus();
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

  const pollBackfillStatus = async () => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_URL}/analytics/backfill/status`);
        const status = await response.json();
        
        setBackfillStatus(status);
        
        if (!status.running) {
          clearInterval(pollInterval);
          // Refresh data when complete
          setTimeout(() => {
            fetchSetupStatus();
            fetchAnalyticsData();
          }, 1000);
        }
      } catch (error) {
        console.error('Error polling backfill status:', error);
        clearInterval(pollInterval);
      }
    }, 1000); // Poll every second
  };

  useEffect(() => {
    fetchSetupStatus();
    fetchAnalyticsData();
    // Removed auto-refresh - users can manually refresh via the refresh button
  }, []);

  // Removed auto-refresh on date/interval changes - user must click Apply button

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
        <div className="max-w-7xl mx-auto mb-4">
          <div className="flex justify-between items-start mb-4">
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
              Back to Dashboard
            </button>
          </div>
          </div>
        </div>

        {/* Critical Warning: No Items */}
        {setupStatus && setupStatus.inventory_items === 0 && (
          <div className="max-w-7xl mx-auto mb-4 bg-red-50 border-2 border-red-200 rounded-lg p-6">
            <div className="flex items-start gap-4">
              <div className="text-4xl">⚠️</div>
              <div className="flex-1">
                <h3 className="text-lg font-bold text-red-900 mb-2">No Inventory Items Found</h3>
                <p className="text-red-800 mb-3">
                  You must generate simulation inventory before creating analytics data. 
                  Analytics (purchases, stock snapshots) are based on items in your store.
                </p>
                <div className="bg-white border border-red-200 rounded p-3 mb-3">
                  <p className="text-sm font-semibold text-gray-900 mb-2">To generate inventory:</p>
                  <ol className="text-sm text-gray-700 space-y-1 list-decimal list-inside">
                    <li>Ensure you're in SIMULATION mode (check main dashboard)</li>
                    <li>Run: <code className="bg-gray-100 px-2 py-0.5 rounded text-xs font-mono">python -m simulation.generate_inventory --items 1000</code></li>
                    <li>Or start the simulation from the main dashboard</li>
                    <li>Then return here to generate analytics data</li>
                  </ol>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Setup Status */}
        {showBackfill && setupStatus && setupStatus.inventory_items > 0 && (
          <div className="max-w-7xl mx-auto mb-4 bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-700">System Status</h3>
              <button
                onClick={() => {
                  fetchSetupStatus();
                  fetchAnalyticsData();
                }}
                className="text-xs px-3 py-1 text-gray-600 hover:text-[#0055A4] hover:bg-gray-50 border border-gray-300 rounded transition-colors flex items-center gap-1"
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
              </button>
            </div>
            <div className="grid grid-cols-5 gap-3 text-sm">
              <div className="flex flex-col">
                <span className="text-gray-500">Products</span>
                <span className="font-semibold text-gray-900">{setupStatus.products.toLocaleString()}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-gray-500">Items</span>
                <span className={`font-semibold ${setupStatus.inventory_items > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {setupStatus.inventory_items.toLocaleString()}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-gray-500">Purchases</span>
                <span className="font-semibold text-gray-900">{setupStatus.purchase_events.toLocaleString()}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-gray-500">Snapshots</span>
                <span className="font-semibold text-gray-900">{setupStatus.stock_snapshots.toLocaleString()}</span>
              </div>
              <div className="flex items-center">
                <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                  setupStatus.setup_complete ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {setupStatus.setup_complete ? '✓ Ready' : '⚠ Setup Needed'}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Backfill Controls */}
        {showBackfill && (
          <div className="max-w-7xl mx-auto mb-4 bg-white rounded-lg shadow p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Data Management</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-5 gap-4 items-end">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Density
                  </label>
                  <select
                    value={backfillDensity}
                    onChange={(e) => setBackfillDensity(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0055A4] focus:border-[#0055A4]"
                    disabled={isBackfilling || setupStatus?.inventory_items === 0}
                  >
                    <option value="sparse">Sparse (20/day)</option>
                    <option value="normal">Normal (50/day)</option>
                    <option value="dense">Dense (100/day)</option>
                    <option value="stress">Stress (300/day)</option>
                    <option value="extreme">Extreme (200/day)</option>
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
                    max="90"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0055A4] focus:border-[#0055A4]"
                    disabled={isBackfilling || setupStatus?.inventory_items === 0}
                  />
                  <p className="text-xs text-gray-500 mt-1">Max 90 days</p>
                </div>
                <div>
                  <button
                    onClick={triggerBackfill}
                    disabled={isBackfilling || setupStatus?.inventory_items === 0}
                    className="w-full px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed rounded-lg transition-colors"
                    title={setupStatus?.inventory_items === 0 ? 'Generate inventory items first' : 'Generate historical analytics data'}
                  >
                    {isBackfilling ? 'Working...' : 'Generate Data'}
                  </button>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={clearData}
                    disabled={isBackfilling}
                    className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:bg-gray-400 rounded-lg transition-colors"
                  >
                    Clear Data
                  </button>
                  {backfillStatus?.running && backfillStatus.total > 0 && (
                    <div className="flex items-center gap-2 text-sm text-gray-700">
                      <div className="font-medium">
                        {backfillStatus.progress.toLocaleString()} / {backfillStatus.total.toLocaleString()}
                      </div>
                      <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-blue-600 transition-all duration-300"
                          style={{ width: `${(backfillStatus.progress / backfillStatus.total) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
                <div>
                  {backfillStatus && (
                    <div className={`text-xs ${backfillStatus.running ? 'text-blue-600' : backfillStatus.records > 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {backfillStatus.message}
                      {backfillStatus.records > 0 && !backfillStatus.running && ` (${backfillStatus.records} records)`}
                    </div>
                  )}
                </div>
              </div>
              
              {/* Info about generated data patterns */}
              {setupStatus && setupStatus.inventory_items > 0 && setupStatus.purchase_events === 0 && (
                <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <div className="text-2xl">ℹ️</div>
                    <div className="flex-1 text-sm">
                      <p className="font-semibold text-blue-900 mb-2">About Generated Analytics Data</p>
                      <p className="text-blue-800 mb-2">
                        The data generator creates realistic Decathlon store patterns including:
                      </p>
                      <ul className="text-blue-800 space-y-1 list-disc list-inside text-xs">
                        <li><strong>Dead stock (15-20%):</strong> Unpopular items with near-zero sales</li>
                        <li><strong>Weekend peaks:</strong> 2-3x higher traffic Sat/Sun for sports items</li>
                        <li><strong>Price-based velocity:</strong> Cheap items sell faster than expensive</li>
                        <li><strong>Seasonal patterns:</strong> Swimming gear slower in winter months</li>
                        <li><strong>Category trends:</strong> Nutrition peaks at lunch, Fitness in mornings</li>
                      </ul>
                      <p className="text-blue-700 mt-2 text-xs italic">
                        This ensures realistic KPIs including low stock alerts, stockout risk, and dead stock analysis.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

      </div>

      {/* Main Content Area with Tabs */}
      <div className="flex-1 px-6 pb-6 overflow-hidden">
        <div className="max-w-7xl mx-auto h-full flex flex-col">
          <div className="bg-white rounded-lg shadow h-full flex flex-col overflow-hidden">
            {/* Tab Navigation with Date Controls */}
            <div className="flex-shrink-0 border-b border-gray-200">
              <div className="flex justify-between items-center">
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

                {/* Date Range and Interval Controls */}
                <div className="flex items-center gap-4 pr-4">
                  {/* Quick Range Buttons */}
                  <div className="flex gap-1">
                    {(['7', '30', '90'] as const).map((days) => (
                      <button
                        key={days}
                        onClick={() => {
                          setDateRange(days);
                          setCustomStartDate('');
                          setCustomEndDate('');
                        }}
                        className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                          dateRange === days
                            ? 'bg-[#0055A4] text-white'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {days}d
                      </button>
                    ))}
                    <button
                      onClick={() => setDateRange('custom')}
                      className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                        dateRange === 'custom'
                          ? 'bg-[#0055A4] text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      Custom
                    </button>
                  </div>

                  {/* Custom Date Inputs */}
                  {dateRange === 'custom' && (
                    <div className="flex items-center gap-2">
                      <input
                        type="date"
                        value={customStartDate}
                        onChange={(e) => setCustomStartDate(e.target.value)}
                        className="px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-[#0055A4]"
                      />
                      <span className="text-xs text-gray-500">to</span>
                      <input
                        type="date"
                        value={customEndDate}
                        onChange={(e) => setCustomEndDate(e.target.value)}
                        className="px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-[#0055A4]"
                      />
                    </div>
                  )}

                  {/* Interval Selector */}
                  <div className="flex gap-1 border-l border-gray-200 pl-4">
                    <span className="text-xs text-gray-500 self-center mr-2">Interval:</span>
                    {(['hour', 'day', 'week', 'month'] as const).map((interval) => (
                      <button
                        key={interval}
                        onClick={() => setTimeInterval(interval)}
                        className={`px-2 py-1.5 text-xs font-medium rounded transition-colors ${
                          timeInterval === interval
                            ? 'bg-[#0055A4] text-white'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                        title={`Aggregate by ${interval}`}
                      >
                        {interval.charAt(0).toUpperCase()}
                      </button>
                    ))}
                  </div>

                  {/* Apply Button */}
                  <button
                    onClick={fetchAnalyticsData}
                    disabled={loading}
                    className="px-4 py-1.5 text-xs font-medium text-white bg-[#0055A4] hover:bg-[#003d7a] disabled:bg-gray-400 rounded-lg transition-colors"
                  >
                    {loading ? 'Loading...' : 'Apply'}
                  </button>
                </div>
              </div>
            </div>

            {/* Tab Content */}
            <div className="flex-1 p-6 overflow-auto">
              {/* KPIs Tab */}
              {activeTab === 'kpis' && (
                <div className="space-y-6">
                  {/* KPI Cards Grid */}
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Key Performance Indicators</h2>
                    <AnalyticsOverview data={analyticsOverview} />
                  </div>

                  {/* Sales Over Time Chart */}
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Sales Over Time</h2>
                    <div className="bg-white border border-gray-200 rounded-lg p-6">
                      <SalesTimeSeriesChart 
                        key={appliedInterval}
                        data={salesTimeSeries} 
                        interval={appliedInterval}
                        isLoading={loading}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Performance Overview Tab */}
              {activeTab === 'overview' && (
                <div className="h-full grid grid-cols-2 gap-4">
                  <div className="bg-white border border-gray-200 rounded-lg p-6 flex flex-col">
                    <h3 className="text-base font-semibold text-gray-900 mb-4">Product Velocity</h3>
                    <div className="flex-1">
                      <ProductVelocityChart data={productVelocity} />
                    </div>
                  </div>

                  <div className="bg-white border border-gray-200 rounded-lg p-6 flex flex-col">
                    <h3 className="text-base font-semibold text-gray-900 mb-4">Category Distribution</h3>
                    <div className="flex-1">
                      <CategoryDonut data={categoryPerformance} />
                    </div>
                  </div>
                </div>
              )}

              {/* Product Analysis Tab */}
              {activeTab === 'products' && (
                <div className="h-full">
                  <ProductAnalytics 
                    data={productVelocity} 
                    onRefresh={fetchAnalyticsData}
                    isLoading={loading}
                  />
                </div>
              )}

              {/* AI Insights Tab */}
              {activeTab === 'ai-insights' && (
                <div className="h-full grid grid-rows-[auto_1fr] gap-4">
                  {/* Anomaly Alerts */}
                  <div>
                    <AnomalyAlerts data={anomalies} />
                  </div>

                  {/* Analysis Grid */}
                  <div className="grid grid-cols-3 gap-4 min-h-0">
                    {/* Product Insights - Takes 2 columns */}
                    <div className="col-span-2 bg-white border border-gray-200 rounded-lg p-6">
                      <ProductInsights data={productVelocity} />
                    </div>

                    {/* Demand Forecast */}
                    <div className="bg-white border border-gray-200 rounded-lg p-6 flex flex-col">
                      <h3 className="text-base font-semibold text-gray-900 mb-2">Demand Forecast</h3>
                      <select
                        value={selectedProductForForecast || ''}
                        onChange={(e) => setSelectedProductForForecast(Number(e.target.value))}
                        className="mb-4 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
