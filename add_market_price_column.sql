-- Add market_price column to materials table
ALTER TABLE materials ADD COLUMN market_price NUMERIC(10,4) DEFAULT 0.0000;