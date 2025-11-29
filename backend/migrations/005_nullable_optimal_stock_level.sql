-- Migration: Make optimal_stock_level nullable
-- Version: 005
-- Description: Change optimal_stock_level to nullable and set existing values to NULL

-- Make optimal_stock_level nullable
ALTER TABLE products ALTER COLUMN optimal_stock_level DROP NOT NULL;
ALTER TABLE products ALTER COLUMN optimal_stock_level DROP DEFAULT;
ALTER TABLE products ALTER COLUMN optimal_stock_level SET DEFAULT NULL;

-- Set all existing values to NULL
UPDATE products SET optimal_stock_level = NULL;
