import React from 'react';

interface ProductData {
  product_id: number;
  sku: string;
  name: string;
  category: string;
  current_stock: number;
  velocity_daily: number;
  turnover_rate: number;
  days_until_stockout: number | null;
}

interface ProductInsightsProps {
  data: ProductData[];
}

export default function ProductInsights({ data }: ProductInsightsProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white border border-gray-300 p-4 h-full">
        <div className="flex items-center justify-between mb-3 pb-3 border-b border-gray-900">
          <h3 className="text-sm font-bold text-gray-900 uppercase">Product Categorization</h3>
        </div>
        <p className="text-xs text-gray-600">No product data available</p>
      </div>
    );
  }

  const restockPriority: ProductData[] = [];
  const deadStockRisk: ProductData[] = [];
  const fastMovers: ProductData[] = [];

  data.forEach(product => {
    const velocity = product.velocity_daily || 0;
    const stock = product.current_stock || 0;
    const daysUntilStockout = product.days_until_stockout;

    if (velocity > 0.5 && (stock < 10 || (daysUntilStockout !== null && daysUntilStockout < 7))) {
      restockPriority.push(product);
    } else if (velocity < 0.1 && stock > 20) {
      deadStockRisk.push(product);
    } else if (velocity > 1) {
      fastMovers.push(product);
    }
  });

  const categories = [
    {
      title: 'RESTOCK PRIORITY',
      count: restockPriority.length,
      products: restockPriority.slice(0, 8),
      priority: 'high'
    },
    {
      title: 'DEAD STOCK RISK',
      count: deadStockRisk.length,
      products: deadStockRisk.slice(0, 8),
      priority: 'medium'
    },
    {
      title: 'FAST MOVERS',
      count: fastMovers.length,
      products: fastMovers.slice(0, 8),
      priority: 'low'
    }
  ];

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-3 pb-3 border-b border-gray-900">
        <h3 className="text-sm font-bold text-gray-900 uppercase">Product Categorization</h3>
        <span className="text-xs text-gray-600">VELOCITY-BASED ANALYSIS</span>
      </div>

      <div className="flex-1 grid grid-cols-3 gap-3 min-h-0">
        {categories.map((category, idx) => (
          <div key={idx} className="border border-gray-300 bg-white flex flex-col">
            <div className={`p-2 flex items-center justify-between border-b border-gray-900 ${
              category.priority === 'high' ? 'bg-black text-white' :
              category.priority === 'medium' ? 'bg-gray-400 text-white' :
              'bg-gray-200 text-gray-900'
            }`}>
              <div className="text-xs font-bold">{category.title}</div>
              <div className="text-xs font-bold">{category.count}</div>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
              {category.products.length > 0 ? (
                category.products.map((product, i) => (
                  <div key={i} className="border border-gray-300 bg-gray-50 p-2">
                    <div className="text-xs font-bold text-gray-900 mb-1 truncate">
                      {product.name}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <div className="text-gray-600">STOCK</div>
                        <div className="font-bold">{product.current_stock}</div>
                      </div>
                      <div>
                        <div className="text-gray-600">VELOCITY</div>
                        <div className="font-bold">{product.velocity_daily.toFixed(1)}</div>
                      </div>
                    </div>
                    {product.days_until_stockout !== null && product.days_until_stockout < 14 && (
                      <div className="mt-1 pt-1 border-t border-gray-300 text-xs font-bold">
                        {product.days_until_stockout}d TO STOCKOUT
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-xs text-gray-500 text-center py-4">NO PRODUCTS</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
