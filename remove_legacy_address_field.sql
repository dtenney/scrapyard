-- Remove legacy address field from customers table
ALTER TABLE customers DROP COLUMN IF EXISTS address;