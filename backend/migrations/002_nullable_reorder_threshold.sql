-- Make reorder_threshold nullable and set existing values to NULL if they are the default
-- This migration allows products to have no restock alerts by default

ALTER TABLE products 
ALTER COLUMN reorder_threshold DROP NOT NULL,
ALTER COLUMN reorder_threshold DROP DEFAULT;

-- Set all existing values to NULL by default (users can set specific thresholds later)
UPDATE products SET reorder_threshold = NULL;

COMMENT ON COLUMN products.reorder_threshold IS 'Alert threshold for restocking - NULL means no alerts';
