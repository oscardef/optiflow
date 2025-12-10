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
      <div className="animate-pulse min-h-[350px]">
        <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
        <div className="h-64 bg-gray-100 rounded"></div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="min-h-[350px]">
        <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
          No sales data available
        </div>
      </div>
    );
  }

  // Calculate chart dimensions and scale
  const sales = data.map(d => d.sales);
  const maxSales = Math.max(...sales, 10); // Minimum scale of 10
  const minSales = 0; // Always start from 0 for sales
  
  // Calculate nice Y-axis scale with round numbers
  const getYAxisScale = (max: number) => {
    // Find a nice round number for max
    const magnitude = Math.pow(10, Math.floor(Math.log10(max)));
    const normalized = max / magnitude;
    
    let niceMax;
    if (normalized <= 1.5) niceMax = 2 * magnitude;
    else if (normalized <= 3) niceMax = 5 * magnitude;
    else if (normalized <= 7) niceMax = 10 * magnitude;
    else niceMax = 20 * magnitude;
    
    const step = niceMax / 5; // 5 intervals
    
    return {
      min: 0,
      max: niceMax,
      step,
      ticks: [0, step, step * 2, step * 3, step * 4, niceMax]
    };
  };
  
  const yAxis = getYAxisScale(maxSales);
  const chartHeight = 300; // Increased height for better readability

  // Format date label based on interval
  const formatDate = (dateStr: string, compact: boolean = false) => {
    const date = new Date(dateStr);
    switch (interval) {
      case 'hour':
        if (compact) {
          return date.toLocaleTimeString('en-US', { hour: 'numeric', hour12: true });
        }
        return date.toLocaleString('en-US', { 
          month: 'short', 
          day: 'numeric', 
          hour: 'numeric', 
          hour12: true 
        });
      case 'day':
        if (compact) {
          return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        }
        return date.toLocaleDateString('en-US', { 
          weekday: 'short', 
          month: 'short', 
          day: 'numeric' 
        });
      case 'week':
        return 'Week of ' + date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
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
  const minPointWidth = interval === 'hour' ? 50 : interval === 'day' ? 40 : 60;
  const calculatedWidth = Math.max(900, data.length * minPointWidth);
  const needsScroll = calculatedWidth > 900;
  
  // Determine how many X-axis labels to show based on data length
  const getXAxisLabels = () => {
    const maxLabels = 8;
    if (data.length <= maxLabels) {
      return data.map((d, idx) => ({ idx, date: d.date }));
    }
    
    const step = Math.ceil(data.length / maxLabels);
    const labels = [];
    for (let i = 0; i < data.length; i += step) {
      labels.push({ idx: i, date: data[i].date });
    }
    // Always include the last point
    if (labels[labels.length - 1].idx !== data.length - 1) {
      labels.push({ idx: data.length - 1, date: data[data.length - 1].date });
    }
    return labels;
  };
  
  const xAxisLabels = getXAxisLabels();

  return (
    <div className="min-h-[350px]">
      <div className="flex justify-between items-start mb-4">
        <div>
          <p className="text-sm text-gray-500">
            {interval === 'hour' && 'Hourly sales trend'}
            {interval === 'day' && 'Daily sales trend'}
            {interval === 'week' && 'Weekly sales trend'}
            {interval === 'month' && 'Monthly sales trend'}
            {needsScroll && <span className="ml-2 text-blue-600">→ Scroll to see all data</span>}
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
      <div className={`${needsScroll ? 'overflow-x-auto pb-2' : ''}`}>
        <div style={{ minWidth: `${calculatedWidth}px` }}>
          <div className="relative" style={{ height: `${chartHeight}px` }}>
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 bottom-0 flex flex-col justify-between text-xs text-gray-600 pr-3 font-medium">
          {yAxis.ticks.reverse().map((tick) => (
            <span key={tick} className="bg-white">{Math.round(tick)}</span>
          ))}
        </div>

        {/* Chart area */}
        <div className="ml-14 h-full border-l-2 border-b-2 border-gray-300 relative bg-gradient-to-b from-blue-50/30 to-white">
          {/* Grid lines */}
          <div className="absolute inset-0">
            {[0, 20, 40, 60, 80, 100].map((percent) => (
              <div
                key={percent}
                className="absolute w-full border-t border-gray-200"
                style={{ top: `${percent}%` }}
              />
            ))}
          </div>

          {/* Area fill under line */}
          <svg 
            className="absolute inset-0 pointer-events-none" 
            width="100%" 
            height="100%" 
            viewBox="0 0 100 100" 
            preserveAspectRatio="none"
          >
            <defs>
              <linearGradient id="areaGradient" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#0055A4" stopOpacity="0.2" />
                <stop offset="100%" stopColor="#0055A4" stopOpacity="0.02" />
              </linearGradient>
            </defs>
            <polygon
              points={
                data.map((point, idx) => {
                  const x = ((idx + 0.5) / data.length) * 100;
                  const y = getYPosition(point.sales);
                  return `${x},${y}`;
                }).join(' ') +
                ` 100,100 0,100`
              }
              fill="url(#areaGradient)"
            />
          </svg>

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
              strokeWidth="0.6"
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
                  {/* Point circle - show all points but make 0 values subtle */}
                  <div 
                    className={`rounded-full shadow-sm hover:scale-150 transition-transform cursor-pointer ${
                      point.sales === 0 
                        ? 'w-2 h-2 bg-gray-300 border border-gray-400' 
                        : 'w-3 h-3 bg-[#0055A4] border-2 border-white shadow-md'
                    }`} 
                  />
                  
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
        <div className="ml-14 mt-3 relative" style={{ height: '40px' }}>
          <div className="relative w-full">
            {xAxisLabels.map(({ idx, date }) => {
              const xPercent = ((idx + 0.5) / data.length) * 100;
              return (
                <div
                  key={idx}
                  className="absolute text-xs text-gray-600 font-medium"
                  style={{
                    left: `${xPercent}%`,
                    transform: 'translateX(-50%)',
                    whiteSpace: 'nowrap'
                  }}
                >
                  <div className="text-center">
                    {formatDate(date, true)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
          </div>
        </div>
      </div>
    </div>
  );
}
