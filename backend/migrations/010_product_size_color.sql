-- Add size and color fields to products table
-- Version: 010
-- Description: Add size and color metadata for Decathlon products

ALTER TABLE products 
ADD COLUMN IF NOT EXISTS size VARCHAR(50);

ALTER TABLE products 
ADD COLUMN IF NOT EXISTS color VARCHAR(50);

COMMENT ON COLUMN products.size IS 'Product size (e.g., S, M, L, 39-42, OneSize)';
COMMENT ON COLUMN products.color IS 'Product color (e.g., Black, Blue, Red)';
