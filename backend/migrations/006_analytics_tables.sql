-- Analytics Tables Migration
-- Adds StockSnapshot and StockMovement tables for time-series analytics

-- Stock Snapshots: Periodic captures of inventory state
CREATE TABLE IF NOT EXISTS stock_snapshots (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    present_count INTEGER DEFAULT 0,
    missing_count INTEGER DEFAULT 0,
    zone_id INTEGER REFERENCES zones(id) ON DELETE SET NULL
);

-- Indexes for efficient time-series queries
CREATE INDEX IF NOT EXISTS idx_stock_snapshots_product_id ON stock_snapshots(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_snapshots_timestamp ON stock_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_stock_snapshots_zone_id ON stock_snapshots(zone_id);
CREATE INDEX IF NOT EXISTS idx_stock_snapshots_product_timestamp ON stock_snapshots(product_id, timestamp);

-- Stock Movements: Detailed tracking of inventory changes
CREATE TABLE IF NOT EXISTS stock_movements (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    movement_type VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- Indexes for movement analytics
CREATE INDEX IF NOT EXISTS idx_stock_movements_product_id ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_timestamp ON stock_movements(timestamp);
CREATE INDEX IF NOT EXISTS idx_stock_movements_type ON stock_movements(movement_type);
CREATE INDEX IF NOT EXISTS idx_stock_movements_product_timestamp ON stock_movements(product_id, timestamp);

-- Comments for documentation
COMMENT ON TABLE stock_snapshots IS 'Hourly/daily snapshots of stock levels for trend analysis';
COMMENT ON TABLE stock_movements IS 'Individual stock change events (sales, restocks, adjustments)';
COMMENT ON COLUMN stock_movements.movement_type IS 'Type: sale, restock, loss, adjustment';
