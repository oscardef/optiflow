-- OptiFlow Inventory Management System Migration
-- Version: 001
-- Description: Add inventory management tables for product tracking, stock levels, restocking, and analytics

-- Products table: Master catalog of all products in the store
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    unit_price DECIMAL(10, 2),
    reorder_threshold INTEGER DEFAULT 10,
    optimal_stock_level INTEGER DEFAULT 50,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_category ON products(category);

-- Inventory items: Individual RFID-tagged items in the store
CREATE TABLE IF NOT EXISTS inventory_items (
    id SERIAL PRIMARY KEY,
    rfid_tag VARCHAR(50) UNIQUE NOT NULL,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'present',  -- present, sold, missing, restocking
    x_position FLOAT,
    y_position FLOAT,
    zone_id INTEGER,  -- Foreign key to zones table
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_inventory_items_rfid ON inventory_items(rfid_tag);
CREATE INDEX idx_inventory_items_product_id ON inventory_items(product_id);
CREATE INDEX idx_inventory_items_status ON inventory_items(status);
CREATE INDEX idx_inventory_items_zone_id ON inventory_items(zone_id);

-- Zones: Store map divided into zones for heat mapping
CREATE TABLE IF NOT EXISTS zones (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    x_min FLOAT NOT NULL,
    y_min FLOAT NOT NULL,
    x_max FLOAT NOT NULL,
    y_max FLOAT NOT NULL,
    zone_type VARCHAR(50),  -- aisle, checkout, entrance, storage
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_zones_type ON zones(zone_type);

-- Stock levels: Aggregated current stock counts per product
CREATE TABLE IF NOT EXISTS stock_levels (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    current_count INTEGER DEFAULT 0,
    missing_count INTEGER DEFAULT 0,
    sold_today INTEGER DEFAULT 0,
    last_restock_at TIMESTAMP,
    priority_score FLOAT DEFAULT 0.0,  -- Calculated priority for restocking
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stock_levels_product_id ON stock_levels(product_id);
CREATE INDEX idx_stock_levels_priority ON stock_levels(priority_score DESC);

-- Restock tasks: Queue of items that need restocking
CREATE TABLE IF NOT EXISTS restock_tasks (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity_requested INTEGER NOT NULL,
    priority_score FLOAT DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, in_progress, completed, cancelled
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    requested_by VARCHAR(100),  -- User or system that requested restock
    notes TEXT
);

CREATE INDEX idx_restock_tasks_status ON restock_tasks(status);
CREATE INDEX idx_restock_tasks_priority ON restock_tasks(priority_score DESC);
CREATE INDEX idx_restock_tasks_product_id ON restock_tasks(product_id);

-- Purchase events: Track when items are sold (for analytics)
CREATE TABLE IF NOT EXISTS purchase_events (
    id SERIAL PRIMARY KEY,
    inventory_item_id INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    x_position FLOAT,  -- Last known position before sale
    y_position FLOAT,
    zone_id INTEGER REFERENCES zones(id),
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_purchase_events_product_id ON purchase_events(product_id);
CREATE INDEX idx_purchase_events_zone_id ON purchase_events(zone_id);
CREATE INDEX idx_purchase_events_timestamp ON purchase_events(purchased_at);

-- Add foreign key constraint to inventory_items for zones
ALTER TABLE inventory_items
ADD CONSTRAINT fk_inventory_items_zone
FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE SET NULL;

-- Create trigger to update stock_levels when inventory_items change
CREATE OR REPLACE FUNCTION update_stock_levels()
RETURNS TRIGGER AS $$
BEGIN
    -- Recalculate stock levels for the affected product
    INSERT INTO stock_levels (product_id, current_count, missing_count, sold_today, updated_at)
    SELECT 
        p.id,
        COUNT(CASE WHEN ii.status = 'present' THEN 1 END),
        COUNT(CASE WHEN ii.status = 'missing' THEN 1 END),
        COUNT(CASE WHEN ii.status = 'sold' AND DATE(ii.updated_at) = CURRENT_DATE THEN 1 END),
        CURRENT_TIMESTAMP
    FROM products p
    LEFT JOIN inventory_items ii ON p.id = ii.product_id
    WHERE p.id = COALESCE(NEW.product_id, OLD.product_id)
    GROUP BY p.id
    ON CONFLICT (product_id) DO UPDATE SET
        current_count = EXCLUDED.current_count,
        missing_count = EXCLUDED.missing_count,
        sold_today = EXCLUDED.sold_today,
        updated_at = EXCLUDED.updated_at;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_stock_levels
AFTER INSERT OR UPDATE OR DELETE ON inventory_items
FOR EACH ROW
EXECUTE FUNCTION update_stock_levels();

-- Add unique constraint to stock_levels to prevent duplicates
ALTER TABLE stock_levels
ADD CONSTRAINT unique_product_stock_level UNIQUE (product_id);

-- Insert default zones for store layout (based on 1000cm x 800cm store)
INSERT INTO zones (name, x_min, y_min, x_max, y_max, zone_type) VALUES
    ('Entrance Area', 0, 0, 200, 200, 'entrance'),
    ('Aisle 1', 200, 100, 400, 700, 'aisle'),
    ('Aisle 2', 400, 100, 600, 700, 'aisle'),
    ('Aisle 3', 600, 100, 800, 700, 'aisle'),
    ('Aisle 4', 800, 100, 1000, 700, 'aisle'),
    ('Cross Aisle', 200, 400, 1000, 500, 'aisle'),
    ('Checkout Area', 0, 700, 1000, 800, 'checkout');

-- Insert sample products (will be expanded by simulator)
INSERT INTO products (sku, name, category, unit_price, reorder_threshold, optimal_stock_level) VALUES
    ('MILK-001', 'Whole Milk 1L', 'Dairy', 3.99, 15, 60),
    ('BREAD-001', 'White Bread', 'Bakery', 2.49, 10, 40),
    ('APPL-001', 'Red Apples', 'Produce', 1.99, 20, 80),
    ('CHIP-001', 'Potato Chips', 'Snacks', 3.49, 15, 50),
    ('SODA-001', 'Cola 2L', 'Beverages', 2.99, 20, 70);

COMMENT ON TABLE products IS 'Master catalog of all products available in the store';
COMMENT ON TABLE inventory_items IS 'Individual RFID-tagged items currently in the store';
COMMENT ON TABLE zones IS 'Store map divided into zones for analytics and heat mapping';
COMMENT ON TABLE stock_levels IS 'Aggregated stock counts and restock priorities per product';
COMMENT ON TABLE restock_tasks IS 'Queue of restocking tasks with priorities';
COMMENT ON TABLE purchase_events IS 'Historical record of item purchases for analytics';
