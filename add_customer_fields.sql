-- Add birthday, gender, and eye_color columns to customers table
ALTER TABLE customers ADD COLUMN birthday DATE;
ALTER TABLE customers ADD COLUMN gender VARCHAR(10);
ALTER TABLE customers ADD COLUMN eye_color VARCHAR(20);