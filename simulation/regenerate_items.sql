-- Generate positions and create items
DO $$
DECLARE
    sku_record RECORD;
    item_num INT := 1;
    total_items INT := 3000;
    items_per_sku INT;
    extra_items INT;
    count_for_sku INT;
    x_pos DECIMAL;
    y_pos DECIMAL;
    rfid_tag VARCHAR;
    total_skus INT;
BEGIN
    -- Count SKUs
    SELECT COUNT(*) INTO total_skus FROM products;
    items_per_sku := total_items / total_skus;
    extra_items := total_items % total_skus;
    
    -- Create temporary table for positions
    CREATE TEMP TABLE temp_positions (
        id SERIAL PRIMARY KEY,
        x DECIMAL(10,2),
        y DECIMAL(10,2)
    );
    
    -- Generate aisle positions (4 aisles, 4 shelves each, both sides, 30 items per shelf)
    -- Aisle 1: x=200, left side
    FOR shelf_level IN 0..3 LOOP
        FOR slot IN 0..29 LOOP
            x_pos := 175;
            y_pos := 150 + (550 * (slot + 0.5) / 30);
            INSERT INTO temp_positions (x, y) VALUES (x_pos, y_pos);
        END LOOP;
    END LOOP;
    
    -- Aisle 1: x=200, right side
    FOR shelf_level IN 0..3 LOOP
        FOR slot IN 0..29 LOOP
            x_pos := 225;
            y_pos := 150 + (550 * (slot + 0.5) / 30);
            INSERT INTO temp_positions (x, y) VALUES (x_pos, y_pos);
        END LOOP;
    END LOOP;
    
    -- Aisle 2: x=400, left side
    FOR shelf_level IN 0..3 LOOP
        FOR slot IN 0..29 LOOP
            x_pos := 375;
            y_pos := 120 + (580 * (slot + 0.5) / 30);
            INSERT INTO temp_positions (x, y) VALUES (x_pos, y_pos);
        END LOOP;
    END LOOP;
    
    -- Aisle 2: x=400, right side
    FOR shelf_level IN 0..3 LOOP
        FOR slot IN 0..29 LOOP
            x_pos := 425;
            y_pos := 120 + (580 * (slot + 0.5) / 30);
            INSERT INTO temp_positions (x, y) VALUES (x_pos, y_pos);
        END LOOP;
    END LOOP;
    
    -- Aisle 3: x=600, left side
    FOR shelf_level IN 0..3 LOOP
        FOR slot IN 0..29 LOOP
            x_pos := 575;
            y_pos := 120 + (580 * (slot + 0.5) / 30);
            INSERT INTO temp_positions (x, y) VALUES (x_pos, y_pos);
        END LOOP;
    END LOOP;
    
    -- Aisle 3: x=600, right side
    FOR shelf_level IN 0..3 LOOP
        FOR slot IN 0..29 LOOP
            x_pos := 625;
            y_pos := 120 + (580 * (slot + 0.5) / 30);
            INSERT INTO temp_positions (x, y) VALUES (x_pos, y_pos);
        END LOOP;
    END LOOP;
    
    -- Aisle 4: x=800, left side
    FOR shelf_level IN 0..3 LOOP
        FOR slot IN 0..29 LOOP
            x_pos := 775;
            y_pos := 120 + (580 * (slot + 0.5) / 30);
            INSERT INTO temp_positions (x, y) VALUES (x_pos, y_pos);
        END LOOP;
    END LOOP;
    
    -- Aisle 4: x=800, right side
    FOR shelf_level IN 0..3 LOOP
        FOR slot IN 0..29 LOOP
            x_pos := 825;
            y_pos := 120 + (580 * (slot + 0.5) / 30);
            INSERT INTO temp_positions (x, y) VALUES (x_pos, y_pos);
        END LOOP;
    END LOOP;
    
    -- Cross aisle positions (left side)
    FOR x_val IN 200..890 BY 30 LOOP
        INSERT INTO temp_positions (x, y) VALUES (x_val, 370);
    END LOOP;
    
    -- Cross aisle positions (right side)
    FOR x_val IN 200..890 BY 30 LOOP
        INSERT INTO temp_positions (x, y) VALUES (x_val, 430);
    END LOOP;
    
    -- Create items for each product
    FOR sku_record IN SELECT id, sku FROM products ORDER BY sku LOOP
        count_for_sku := items_per_sku;
        IF item_num <= extra_items THEN
            count_for_sku := count_for_sku + 1;
        END IF;
        
        FOR i IN 1..count_for_sku LOOP
            rfid_tag := 'RFID' || LPAD(item_num::TEXT, 8, '0');
            
            -- Get a random position
            SELECT x, y INTO x_pos, y_pos 
            FROM temp_positions 
            ORDER BY random() 
            LIMIT 1;
            
            INSERT INTO inventory_items (rfid_tag, product_id, status, x_position, y_position)
            VALUES (rfid_tag, sku_record.id, 'present', x_pos, y_pos);
            
            item_num := item_num + 1;
            
            EXIT WHEN item_num > total_items;
        END LOOP;
        
        EXIT WHEN item_num > total_items;
    END LOOP;
    
    RAISE NOTICE 'Successfully created % inventory items', item_num - 1;
END $$;
