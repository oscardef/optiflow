// Type definitions for OptiFlow

export interface Anchor {
  id: number;
  mac_address: string;
  name: string;
  x_position: number;
  y_position: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Position {
  id: number;
  tag_id: string;
  x_position: number;
  y_position: number;
  confidence: number;
  timestamp: string;
  num_anchors: number;
}

export interface Item {
  product_id: string;
  product_name: string;
  x_position: number;
  y_position: number;
  status: string;
}

export interface Product {
  id: number;
  sku: string;
  name: string;
  category: string;
  unit_price?: number;
  reorder_threshold: number;
  optimal_stock_level: number;
  created_at: string;
  updated_at: string;
  current_stock?: number;
}

export interface Zone {
  id: number;
  name: string;
  description?: string;
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
  zone_type?: string;
  created_at: string;
}

export type ConfigMode = 'SIMULATION' | 'REAL';

export interface ModeResponse {
  mode: ConfigMode;
  simulation_running: boolean;
}

export interface StoreConfig {
  store_width: number;
  store_height: number;
  mode: ConfigMode;
}

export interface StoreLayout {
  mode: ConfigMode;
  store_width: number;
  store_height: number;
  zones: Zone[];
  anchors: Anchor[];
}

export interface SimulationStatus {
  running: boolean;
  pid?: number;
  mode: ConfigMode;
  uptime_seconds?: number;
}

export interface SystemInfo {
  simulation_db_items: number;
  real_db_items: number;
  simulation_db_products: number;
  real_db_products: number;
  api_status: string;
  current_mode: ConfigMode;
}

export interface AnchorValidation {
  valid: boolean;
  configured_anchors: string[];
  received_anchors: string[];
  warnings: string[];
  message: string;
}

export type ViewMode = 'live' | 'stock-heatmap' | 'restock-queue';

export interface HeatmapEntry {
  product_id: number;
  product_name: string;
  product_category: string;
  zone_id: number;
  zone_name: string;
  zone: Zone;
  x: number;
  y: number;
  current_count: number;
  max_items_seen: number;
  items_missing: number;
  depletion_percentage: number;
}
