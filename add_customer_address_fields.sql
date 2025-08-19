-- Add separate address fields to customers table
ALTER TABLE customers ADD COLUMN street_address VARCHAR(200);
ALTER TABLE customers ADD COLUMN city VARCHAR(100);
ALTER TABLE customers ADD COLUMN state VARCHAR(2);
ALTER TABLE customers ADD COLUMN zip_code VARCHAR(10);
ALTER TABLE customers ADD COLUMN county VARCHAR(100);

-- Migrate existing address data (basic parsing)
UPDATE customers 
SET street_address = TRIM(SUBSTRING(address FROM 1 FOR POSITION(',' IN address || ',') - 1))
WHERE address IS NOT NULL AND address != '';

-- Create index for faster searches
CREATE INDEX idx_customers_address ON customers(city, state, zip_code);
CREATE INDEX idx_customers_search ON customers(name, drivers_license_number, phone);