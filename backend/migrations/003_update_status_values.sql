-- Migration: Update status values from 'present/sold/missing' to 'available/missing'
-- Date: 2025-11-28

-- Update existing 'present' to 'available'
UPDATE inventory_items SET status = 'available' WHERE status = 'present';

-- Update existing 'sold' to 'missing' (since sold items are no longer tracked separately)
UPDATE inventory_items SET status = 'missing' WHERE status = 'sold';

-- Note: The status column will now only use 'available' and 'missing' values
-- No column type change needed as it's already VARCHAR
