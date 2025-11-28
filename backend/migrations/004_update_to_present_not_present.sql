-- Migration: Update status values to 'present' and 'not present'
-- Date: 2025-11-28

-- Update existing 'available' to 'present'
UPDATE inventory_items SET status = 'present' WHERE status = 'available';

-- Update existing 'missing' to 'not present'
UPDATE inventory_items SET status = 'not present' WHERE status = 'missing';
