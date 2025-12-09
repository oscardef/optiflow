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

interface InsightCategory {
  title: string;
  description: string;
  color: string;
  borderColor: string;
  bgColor: string;
  products: ProductData[];
  actionLabel: string;
  priority: 'high' | 'medium' | 'low';
}

export default function ProductInsights({ data }: ProductInsightsProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold mb-4">Product Insights</h3>
        <div className="h-64 flex items-center justify-center text-gray-400">
          No product data available
        </div>
      </div>
    );
  }

  // Categorize products based on velocity and stock levels
  const restockPriority: ProductData[] = [];
  const deadStockRisk: ProductData[] = [];
  const healthyProducts: ProductData[] = [];
  const hotMovers: ProductData[] = [];

  data.forEach(product => {
    const velocity = product.velocity_daily || 0;
    const stock = product.current_stock || 0;
    const daysUntilStockout = product.days_until_stockout;

    // High velocity + low stock (or stockout risk) = Restock Priority
    if (velocity > 0.5 && (stock < 10 || (daysUntilStockout !== null && daysUntilStockout < 7))) {
      restockPriority.push(product);
    }
    // Low velocity + high stock = Dead Stock Risk
    else if (velocity < 0.1 && stock > 20) {
      deadStockRisk.push(product);
    }
    // High velocity + healthy stock = Hot Movers
    else if (velocity > 1 && stock >= 10) {
      hotMovers.push(product);
    }
    // Everything else = Healthy
    else {
      healthyProducts.push(product);
    }
  });

  const categories: InsightCategory[] = [
    {
      title: 'Restock Priority',
      description: 'High-demand products with low stock or approaching stockout',
      color: 'text-red-700',
      borderColor: 'border-red-300',
      bgColor: 'bg-red-50',
      products: restockPriority.sort((a, b) => (b.velocity_daily || 0) - (a.velocity_daily || 0)).slice(0, 5),
      actionLabel: 'Immediate Reorder Required',
      priority: 'high'
    },
    {
      title: 'Dead Stock Risk',
      description: 'Low-velocity products with excess inventory',
      color: 'text-orange-700',
      borderColor: 'border-orange-300',
      bgColor: 'bg-orange-50',
      products: deadStockRisk.sort((a, b) => (b.current_stock || 0) - (a.current_stock || 0)).slice(0, 5),
      actionLabel: 'Consider Discounts or Promotions',
      priority: 'medium'
    },
    {
      title: 'Hot Movers',
      description: 'Fast-selling products with healthy inventory levels',
      color: 'text-green-700',
      borderColor: 'border-green-300',
      bgColor: 'bg-green-50',
      products: hotMovers.sort((a, b) => (b.velocity_daily || 0) - (a.velocity_daily || 0)).slice(0, 5),
      actionLabel: 'Monitor for Future Growth',
      priority: 'low'
    },
    {
      title: 'Healthy Products',
      description: 'Products with balanced velocity and stock levels',
      color: 'text-blue-700',
      borderColor: 'border-blue-300',
      bgColor: 'bg-blue-50',
      products: healthyProducts.slice(0, 5),
      actionLabel: 'No Action Required',
      priority: 'low'
    }
  ];

  return (
    <div className="h-full flex flex-col">
      <div className="mb-4">
        <h3 className="text-base font-semibold text-gray-900">Inventory Insights</h3>
        <p className="text-sm text-gray-600">Products categorized by velocity and stock levels</p>
      </div>

      <div className="flex-1 grid grid-cols-2 gap-4 min-h-0">
        {categories.map((category, idx) => (
          <div
            key={idx}
            className={`border-2 ${category.borderColor} ${category.bgColor} rounded-lg p-4 flex flex-col`}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <h4 className={`text-sm font-semibold ${category.color}`}>
                  {category.title}
                </h4>
                <p className="text-xs text-gray-600 mt-1">{category.description}</p>
              </div>
              <span className={`px-2 py-1 text-xs font-medium rounded ${
                category.priority === 'high' ? 'bg-red-100 text-red-700' :
                category.priority === 'medium' ? 'bg-orange-100 text-orange-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {category.products.length} {category.products.length === 1 ? 'product' : 'products'}
              </span>
            </div>

            {category.products.length > 0 ? (
              <>
                <div className="flex-1 space-y-2 overflow-y-auto">
                  {category.products.map((product, i) => (
                    <div key={i} className="bg-white rounded border border-gray-200 p-2">
                      <div className="flex justify-between items-start mb-1">
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-gray-900 truncate">
                            {product.name}
                          </p>
                          <p className="text-xs text-gray-500">{product.category}</p>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs mt-2">
                        <div>
                          <span className="text-gray-500">Stock:</span>
                          <span className="ml-1 font-medium">{product.current_stock}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Velocity:</span>
                          <span className="ml-1 font-medium">{product.velocity_daily.toFixed(1)}/day</span>
                        </div>
                      </div>
                      {product.days_until_stockout !== null && product.days_until_stockout < 14 && (
                        <div className="mt-2 text-xs">
                          <span className={`font-medium ${
                            product.days_until_stockout < 7 ? 'text-red-600' : 'text-orange-600'
                          }`}>
                            {product.days_until_stockout} days until stockout
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <p className="text-xs font-medium text-gray-700">
                    {category.actionLabel}
                  </p>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-400 text-xs">
                No products in this category
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-4 text-xs text-gray-500 border-t pt-3">
        <p className="font-medium mb-1">Classification Rules:</p>
        <ul className="space-y-1 pl-4 list-disc">
          <li>Restock Priority: Velocity &gt; 2 units/day AND (Stock &lt; 10 OR Days until stockout &lt; 7)</li>
          <li>Dead Stock Risk: Velocity &lt; 0.5 units/day AND Stock &gt; 20 units</li>
          <li>Hot Movers: Velocity &gt; 3 units/day AND Stock ≥ 10 units</li>
          <li>Healthy Products: All other products with balanced metrics</li>
        </ul>
      </div>
    </div>
  );
}
