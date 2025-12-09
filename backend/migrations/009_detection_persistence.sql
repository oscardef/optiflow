-- OptiFlow Detection Persistence Migration
-- Version: 009
-- Description: Add fields to inventory_items for production-ready missing item detection
-- These fields persist detection state across backend restarts for reliable inference

-- Add consecutive_misses: Tracks how many scan cycles missed detecting this item
-- When scanner is in range but item not detected, this increments
-- Resets to 0 when item IS detected
ALTER TABLE inventory_items 
ADD COLUMN IF NOT EXISTS consecutive_misses INTEGER DEFAULT 0;

-- Add last_detection_rssi: The RSSI (signal strength) when item was last detected
-- Negative values in dBm (e.g., -45 is strong, -70 is weak)
-- NULL means item has never been detected
-- Value of 0 typically means tag is not present (used in simulation)
ALTER TABLE inventory_items 
ADD COLUMN IF NOT EXISTS last_detection_rssi FLOAT;

-- Add first_miss_at: Timestamp when consecutive misses started
-- Used to enforce minimum time before marking item as missing
-- NULL when consecutive_misses is 0
ALTER TABLE inventory_items 
ADD COLUMN IF NOT EXISTS first_miss_at TIMESTAMP;

-- Create index for efficient queries on items with pending misses
CREATE INDEX IF NOT EXISTS idx_inventory_items_consecutive_misses 
ON inventory_items(consecutive_misses) 
WHERE consecutive_misses > 0;

-- Reset all detection tracking fields to fresh state
-- This ensures clean start after migration
UPDATE inventory_items SET 
    consecutive_misses = 0,
    last_detection_rssi = NULL,
    first_miss_at = NULL;

COMMENT ON COLUMN inventory_items.consecutive_misses IS 'Count of scan cycles where item was in range but not detected. Resets on detection.';
COMMENT ON COLUMN inventory_items.last_detection_rssi IS 'Last RFID signal strength in dBm. Negative values normal (-30 to -70). 0 means not present.';
COMMENT ON COLUMN inventory_items.first_miss_at IS 'Timestamp when consecutive misses started. NULL when consecutive_misses is 0.';
