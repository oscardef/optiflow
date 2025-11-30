import React from 'react';

interface AnalyticsOverviewProps {
  data: {
    total_products: number;
    total_stock_value: number;
    items_needing_restock: number;
    sales_today: number;
    sales_last_7_days: number;
    sales_last_30_days: number;
  } | null;
}

export default function AnalyticsOverview({ data }: AnalyticsOverviewProps) {
  if (!data) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-24 mb-2"></div>
            <div className="h-8 bg-gray-200 rounded w-16"></div>
          </div>
        ))}
      </div>
    );
  }

  const cards = [
    {
      title: 'Total Products',
      value: data.total_products,
      subtitle: `$${data.total_stock_value.toLocaleString()} value`,
      color: 'blue',
      icon: '📦'
    },
    {
      title: 'Restock Needed',
      value: data.items_needing_restock,
      subtitle: 'Items below threshold',
      color: data.items_needing_restock > 10 ? 'red' : 'yellow',
      icon: '⚠️'
    },
    {
      title: 'Sales Today',
      value: data.sales_today,
      subtitle: `${data.sales_last_7_days} last 7 days`,
      color: 'green',
      icon: '📈'
    },
    {
      title: 'Monthly Sales',
      value: data.sales_last_30_days,
      subtitle: `${(data.sales_last_30_days / 30).toFixed(1)} per day`,
      color: 'purple',
      icon: '💰'
    }
  ];

  const colorClasses = {
    blue: 'bg-blue-50 border-blue-200 text-blue-900',
    red: 'bg-red-50 border-red-200 text-red-900',
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-900',
    green: 'bg-green-50 border-green-200 text-green-900',
    purple: 'bg-purple-50 border-purple-200 text-purple-900'
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((card, index) => (
        <div
          key={index}
          className={`${colorClasses[card.color as keyof typeof colorClasses]} rounded-lg border-2 p-6 shadow-sm hover:shadow-md transition-shadow`}
        >
          <div className="flex justify-between items-start mb-2">
            <h3 className="text-sm font-medium opacity-75">{card.title}</h3>
            <span className="text-2xl">{card.icon}</span>
          </div>
          <div className="text-3xl font-bold mb-1">{card.value.toLocaleString()}</div>
          <div className="text-xs opacity-60">{card.subtitle}</div>
        </div>
      ))}
    </div>
  );
}
