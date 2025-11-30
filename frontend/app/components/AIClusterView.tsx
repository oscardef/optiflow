import React from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface AIClusterViewProps {
  data: {
    clusters: Array<{
      cluster_id: number;
      size: number;
      avg_velocity: number;
      avg_stock: number;
      products: Array<{
        product_id: number;
        name: string;
        velocity: number;
        stock: number;
      }>;
    }>;
  } | null;
}

const CLUSTER_COLORS = ['#0055A4', '#FF6B35', '#4ECDC4', '#F38181', '#95E1D3', '#FFD93D'];

export default function AIClusterView({ data }: AIClusterViewProps) {
  if (!data || !data.clusters || data.clusters.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">AI Product Clustering</h3>
        <div className="h-64 flex items-center justify-center text-gray-400">
          No clustering data available
        </div>
      </div>
    );
  }

  // Flatten all products with their cluster info
  const scatterData = data.clusters.flatMap(cluster => 
    cluster.products.map(product => ({
      x: product.velocity,
      y: product.stock,
      name: product.name,
      cluster: cluster.cluster_id,
      color: CLUSTER_COLORS[cluster.cluster_id % CLUSTER_COLORS.length]
    }))
  );

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">AI Product Clustering</h3>
        <span className="text-sm text-purple-600 font-medium">K-Means Algorithm</span>
      </div>
      
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            type="number" 
            dataKey="x" 
            name="Velocity" 
            label={{ value: 'Velocity (units/day)', position: 'insideBottom', offset: -10 }}
          />
          <YAxis 
            type="number" 
            dataKey="y" 
            name="Stock" 
            label={{ value: 'Current Stock', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip 
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
                    <p className="font-semibold text-sm">{data.name}</p>
                    <p className="text-xs text-purple-600">Cluster {data.cluster}</p>
                    <p className="text-xs text-gray-600">Velocity: {data.x.toFixed(2)}</p>
                    <p className="text-xs text-gray-600">Stock: {data.y}</p>
                  </div>
                );
              }
              return null;
            }}
            cursor={{ strokeDasharray: '3 3' }}
          />
          <Scatter name="Products" data={scatterData} fill="#8884d8">
            {scatterData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
        {data.clusters.map((cluster, index) => (
          <div 
            key={cluster.cluster_id} 
            className="p-2 rounded border"
            style={{ borderColor: CLUSTER_COLORS[index % CLUSTER_COLORS.length] }}
          >
            <div className="flex items-center mb-1">
              <div 
                className="w-3 h-3 rounded-full mr-2" 
                style={{ backgroundColor: CLUSTER_COLORS[index % CLUSTER_COLORS.length] }}
              />
              <span className="font-semibold">Cluster {cluster.cluster_id}</span>
            </div>
            <p className="text-xs text-gray-600">{cluster.size} products</p>
            <p className="text-xs text-gray-600">Avg velocity: {cluster.avg_velocity.toFixed(2)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
