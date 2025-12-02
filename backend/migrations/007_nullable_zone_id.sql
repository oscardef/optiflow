-- Make zone_id nullable in product_location_history table
-- This allows tracking items that don't have an assigned zone

ALTER TABLE product_location_history 
ALTER COLUMN zone_id DROP NOT NULL;
