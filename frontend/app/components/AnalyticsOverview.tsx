import React from 'react';
import InfoTooltip from './InfoTooltip';

interface AnalyticsOverviewProps {
  data: {
    total_products: number;
    total_stock_value: number;
    items_needing_restock: number;
    low_stock_items: number;
    avg_stock_level: number;
    avg_coverage_days: number;
    stockout_risk_items: number;
    dead_stock_count: number;
    avg_turnover_rate: number;
    total_items_tracked: number;
    present_items: number;
    sales_today: number;
    sales_last_7_days: number;
    sales_last_30_days: number;
  } | null;
}

export default function AnalyticsOverview({ data }: AnalyticsOverviewProps) {
  if (!data) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((i) => (
          <div key={i} className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
            <div className="h-3 bg-gray-200 rounded w-24 mb-3"></div>
            <div className="h-8 bg-gray-200 rounded w-20 mb-2"></div>
            <div className="h-3 bg-gray-100 rounded w-32"></div>
          </div>
        ))}
      </div>
    );
  }

  const cards = [
    {
      title: 'Total Products',
      value: data.total_products,
      subtitle: `$${data.total_stock_value.toLocaleString()} total value`,
      tooltip: 'Total number of unique product variants in your inventory, along with the combined value of all stock.',
      trend: null
    },
    {
      title: 'Restock Needed',
      value: data.items_needing_restock,
      subtitle: 'Items below threshold',
      tooltip: 'Number of products that have fallen below their reorder threshold and need immediate restocking.',
      trend: data.items_needing_restock > 10 ? 'critical' : data.items_needing_restock > 0 ? 'warning' : null
    },
    {
      title: 'Low Stock Items',
      value: data.low_stock_items,
      subtitle: 'Approaching threshold',
      tooltip: 'Products approaching their reorder threshold (within 150% of threshold). Monitor these to prevent stockouts.',
      trend: data.low_stock_items > 15 ? 'warning' : null
    },
    {
      title: 'Stockout Risk',
      value: data.stockout_risk_items,
      subtitle: 'Less than 7 days left',
      tooltip: 'Products that will run out in less than 7 days based on current sales velocity. Take immediate action.',
      trend: data.stockout_risk_items > 5 ? 'critical' : data.stockout_risk_items > 0 ? 'warning' : null
    },
    {
      title: 'Stock Coverage',
      value: data.avg_coverage_days.toFixed(1),
      subtitle: 'Days until stockout',
      tooltip: 'Average number of days your current stock will last based on recent sales velocity. Higher is better.',
      trend: null
    },
    {
      title: 'Avg Stock Level',
      value: Math.round(data.avg_stock_level),
      subtitle: 'Units per product',
      tooltip: 'Average inventory level across all products. Helps you understand overall stock depth.',
      trend: null
    },
    {
      title: 'Dead Stock',
      value: data.dead_stock_count,
      subtitle: 'No sales in 30 days',
      tooltip: 'Products with inventory but no sales in the last 30 days. Consider discounting or discontinuing.',
      trend: data.dead_stock_count > 10 ? 'warning' : null
    },
    {
      title: 'Turnover Rate',
      value: data.avg_turnover_rate.toFixed(2),
      subtitle: 'Weekly average',
      tooltip: 'Average inventory turnover rate per week. Higher values indicate faster-moving inventory.',
      trend: null
    },
    {
      title: 'Items Tracked',
      value: data.total_items_tracked,
      subtitle: `${data.present_items} present`,
      tooltip: 'Total individual items tracked by RFID, with count of items currently detected in the system.',
      trend: null
    },
    {
      title: 'Sales Today',
      value: data.sales_today,
      subtitle: `${data.sales_last_7_days} in last 7 days`,
      tooltip: 'Total sales transactions completed today, with a comparison to the past week\'s performance.',
      trend: null
    },
    {
      title: 'Weekly Sales',
      value: data.sales_last_7_days,
      subtitle: `${(data.sales_last_7_days / 7).toFixed(1)} per day avg`,
      tooltip: 'Total sales over the last 7 days with the daily average for this week.',
      trend: null
    },
    {
      title: 'Monthly Sales',
      value: data.sales_last_30_days,
      subtitle: `${(data.sales_last_30_days / 30).toFixed(1)} per day avg`,
      tooltip: 'Total sales over the last 30 days with the daily average, helping you understand sales velocity and trends.',
      trend: null
    }
  ];

  return (
    <div className="grid grid-cols-3 gap-4">
      {cards.map((card, index) => (
        <div
          key={index}
          className="bg-white rounded-lg border border-gray-200 p-5 hover:border-gray-300 transition-colors"
        >
          {/* Header with title and info tooltip */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-1.5">
              <h3 className="text-sm font-medium text-gray-600">
                {card.title}
              </h3>
              <InfoTooltip content={card.tooltip} />
            </div>
            {card.trend === 'critical' && (
              <span className="inline-block w-2 h-2 rounded-full bg-red-500"></span>
            )}
            {card.trend === 'warning' && (
              <span className="inline-block w-2 h-2 rounded-full bg-yellow-500"></span>
            )}
          </div>

          {/* Main value */}
          <div className="text-3xl font-semibold text-gray-900 mb-1.5">
            {card.value.toLocaleString()}
          </div>

          {/* Subtitle */}
          <div className="text-sm text-gray-500">
            {card.subtitle}
          </div>
        </div>
      ))}
    </div>
  );
}
