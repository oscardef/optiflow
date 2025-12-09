-- Migration 008: Remove zones system entirely
-- Zones were designed for predefined store layouts (aisles) which don't apply to production mode
-- Replace with spatial clustering based on x/y positions

-- Remove zone_id foreign keys from all tables
ALTER TABLE inventory_items DROP CONSTRAINT IF EXISTS inventory_items_zone_id_fkey;
ALTER TABLE inventory_items DROP COLUMN IF EXISTS zone_id;

ALTER TABLE purchase_events DROP CONSTRAINT IF EXISTS purchase_events_zone_id_fkey;
ALTER TABLE purchase_events DROP COLUMN IF EXISTS zone_id;

ALTER TABLE product_location_history DROP CONSTRAINT IF EXISTS product_location_history_zone_id_fkey;
ALTER TABLE product_location_history DROP COLUMN IF EXISTS zone_id;

-- Drop zones table
DROP TABLE IF EXISTS zones CASCADE;

-- Update product_location_history to use spatial grid clustering instead
-- Add grid cell identifiers (50cm x 50cm cells)
ALTER TABLE product_location_history ADD COLUMN IF NOT EXISTS grid_x INTEGER;
ALTER TABLE product_location_history ADD COLUMN IF NOT EXISTS grid_y INTEGER;

-- Create index on grid cells for faster clustering queries
CREATE INDEX IF NOT EXISTS idx_product_location_grid ON product_location_history(product_id, grid_x, grid_y);

COMMENT ON COLUMN product_location_history.grid_x IS 'Spatial grid cell X coordinate (50cm cells)';
COMMENT ON COLUMN product_location_history.grid_y IS 'Spatial grid cell Y coordinate (50cm cells)';
