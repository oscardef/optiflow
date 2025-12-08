'use client';

interface TimeSeriesData {
  date: string;
  sales: number;
  revenue: number;
}

interface Props {
  data: TimeSeriesData[];
  interval: 'hour' | 'day' | 'week' | 'month';
  isLoading?: boolean;
}

export default function SalesTimeSeriesChart({ data, interval, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="h-64 bg-gray-100 rounded"></div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold mb-4">Sales Over Time</h3>
        <div className="flex items-center justify-center h-64 text-gray-400">
          No sales data available
        </div>
      </div>
    );
  }

  // Calculate chart dimensions and scale
  const sales = data.map(d => d.sales);
  const maxSales = Math.max(...sales);
  const minSales = Math.min(...sales);
  
  // Calculate nice Y-axis scale
  const getYAxisScale = (min: number, max: number) => {
    const range = max - min;
    const niceRange = range === 0 ? 10 : Math.ceil(range * 1.1); // Add 10% padding
    const step = Math.ceil(niceRange / 4);
    return {
      min: Math.max(0, Math.floor(min - range * 0.05)),
      max: Math.ceil(max + range * 0.05),
      step
    };
  };
  
  const yAxis = getYAxisScale(minSales, maxSales);
  const chartHeight = 256;

  // Format date label based on interval
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    switch (interval) {
      case 'hour':
        return date.toLocaleString('en-US', { 
          month: 'short', 
          day: 'numeric', 
          hour: 'numeric', 
          hour12: true 
        });
      case 'day':
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      case 'week':
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      case 'month':
        return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      default:
        return dateStr;
    }
  };

  // Calculate point positions for the line
  const getYPosition = (sales: number) => {
    const range = yAxis.max - yAxis.min;
    return range === 0 ? 50 : ((yAxis.max - sales) / range) * 100;
  };

  // Calculate minimum width needed for proper data display
  // More data points = need more horizontal space
  const minPointWidth = interval === 'hour' ? 40 : 30; // Pixels per data point
  const calculatedWidth = Math.max(800, data.length * minPointWidth);
  const needsScroll = calculatedWidth > 800;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 min-h-[400px]">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Sales Over Time</h3>
          <p className="text-sm text-gray-500 mt-1">
            {interval === 'hour' && 'Hourly sales'}
            {interval === 'day' && 'Daily sales'}
            {interval === 'week' && 'Weekly sales'}
            {interval === 'month' && 'Monthly sales'}
            {needsScroll && <span className="ml-2 text-[#0055A4]">→ Scroll to see all data</span>}
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-gray-900">
            {data.reduce((sum, d) => sum + d.sales, 0)}
          </p>
          <p className="text-sm text-gray-500">Total sales</p>
        </div>
      </div>

      {/* Chart Container with horizontal scroll */}
      <div className={`${needsScroll ? 'overflow-x-auto' : ''}`}>
        <div style={{ minWidth: `${calculatedWidth}px` }}>
          <div className="relative" style={{ height: `${chartHeight}px` }}>
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 bottom-0 flex flex-col justify-between text-xs text-gray-500 pr-2 font-medium">
          <span>{yAxis.max}</span>
          <span>{Math.round(yAxis.max - yAxis.step)}</span>
          <span>{Math.round(yAxis.max - yAxis.step * 2)}</span>
          <span>{Math.round(yAxis.max - yAxis.step * 3)}</span>
          <span>{yAxis.min}</span>
        </div>

        {/* Chart area */}
        <div className="ml-12 h-full border-l border-b border-gray-200 relative">
          {/* Grid lines */}
          <div className="absolute inset-0">
            {[0, 25, 50, 75, 100].map((percent) => (
              <div
                key={percent}
                className="absolute w-full border-t border-gray-100"
                style={{ top: `${percent}%` }}
              />
            ))}
          </div>

          {/* Line connecting points */}
          <svg 
            className="absolute inset-0 pointer-events-none" 
            width="100%" 
            height="100%" 
            viewBox="0 0 100 100" 
            preserveAspectRatio="none"
            style={{ overflow: 'visible' }}
          >
            <polyline
              points={data.map((point, idx) => {
                const x = ((idx + 0.5) / data.length) * 100;
                const y = getYPosition(point.sales);
                return `${x},${y}`;
              }).join(' ')}
              fill="none"
              stroke="#0055A4"
              strokeWidth="0.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          </svg>

          {/* Data points */}
          <div className="absolute inset-0">
            {data.map((point, idx) => {
              const xPercent = ((idx + 0.5) / data.length) * 100;
              const yPercent = getYPosition(point.sales);
              
              return (
                <div
                  key={idx}
                  className="absolute group"
                  style={{
                    left: `${xPercent}%`,
                    top: `${yPercent}%`,
                    transform: 'translate(-50%, -50%)'
                  }}
                >
                  {/* Point circle */}
                  <div className="w-3 h-3 bg-[#0055A4] border-2 border-white rounded-full shadow-md hover:scale-150 transition-transform cursor-pointer" />
                  
                  {/* Tooltip on hover */}
                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-3 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10 shadow-lg">
                    <div className="font-semibold text-sm">{point.sales} sales</div>
                    <div className="text-gray-300">${point.revenue.toFixed(2)}</div>
                    <div className="text-gray-400 text-xs mt-1">{formatDate(point.date)}</div>
                    {/* Arrow */}
                    <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-px">
                      <div className="border-4 border-transparent border-t-gray-900"></div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* X-axis labels */}
        <div className="ml-12 mt-2 flex justify-between text-xs text-gray-400">
          {data.length > 0 && (
            <>
              <span>{formatDate(data[0].date)}</span>
              {data.length > 2 && data.length < 20 && (
                <span>{formatDate(data[Math.floor(data.length / 2)].date)}</span>
              )}
              <span>{formatDate(data[data.length - 1].date)}</span>
            </>
          )}
        </div>
          </div>
        </div>
      </div>
    </div>
  );
}
