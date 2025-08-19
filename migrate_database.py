#!/usr/bin/env python3
"""
Database migration script to update existing tables with new columns
"""

import psycopg2
from urllib.parse import urlparse
from config.settings import Config

def migrate_database():
    """Add missing columns to existing tables"""
    
    # Parse database URL using urllib.parse
    db_url = Config.SQLALCHEMY_DATABASE_URI
    parsed = urlparse(db_url)
    
    host = parsed.hostname
    port = parsed.port or 5432
    database = parsed.path.lstrip('/')
    username = parsed.username
    password = parsed.password
    
    conn = None
    cursor = None
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password
        )
        
        cursor = conn.cursor()
    
    try:
        # Add missing columns to devices table
        cursor.execute("""
            ALTER TABLE devices 
            ADD COLUMN IF NOT EXISTS serial_port INTEGER DEFAULT 23,
            ADD COLUMN IF NOT EXISTS printer_model VARCHAR(50),
            ADD COLUMN IF NOT EXISTS camera_model VARCHAR(50),
            ADD COLUMN IF NOT EXISTS stream_url VARCHAR(200);
        """)
        
        # Add ferrous column to materials table
        cursor.execute("""
            ALTER TABLE materials 
            ADD COLUMN IF NOT EXISTS is_ferrous BOOLEAN DEFAULT FALSE;
        """)
        
        # Update existing materials with ferrous classification
        cursor.execute("""
            UPDATE materials 
            SET is_ferrous = TRUE 
            WHERE category = 'TRUCK SCALE';
        """)
        
        # Create competitive prices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competitive_prices (
                id SERIAL PRIMARY KEY,
                material_id INTEGER REFERENCES materials(id),
                price_per_pound DECIMAL(10,4) NOT NULL,
                source VARCHAR(50) NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Add customer address columns
        cursor.execute("""
            ALTER TABLE customers 
            ADD COLUMN IF NOT EXISTS street_address VARCHAR(200),
            ADD COLUMN IF NOT EXISTS city VARCHAR(100),
            ADD COLUMN IF NOT EXISTS state VARCHAR(2),
            ADD COLUMN IF NOT EXISTS zip_code VARCHAR(10);
        """)
        
        # Migrate existing address data if needed
        cursor.execute("""
            UPDATE customers 
            SET street_address = address 
            WHERE street_address IS NULL AND address IS NOT NULL;
        """)
        
        print("Added missing columns to devices table")
        print("Added ferrous classification to materials table")
        print("Added customer address columns")
        print("Created competitive prices table")
        
        # Update material prices from CSV data
        csv_prices = {
            '1001': 0.3000, '1002': 0.1500, '1003': 0.1000, '1004': 0.1000, '1005': 0.1000,
            '1006': 0.2000, '1007': 0.0900, '1008': 0.1000, '1009': 0.0700, '101': 0.5500,
            '1010': 0.2500, '1011': 0.1000, '1012': 0.4000, '1013': 0.3000, '1014': 0.5500,
            '1015': 0.0000, '1016': 4.0000, '1017': 0.0500, '1018': 0.0000, '1019': 0.0900,
            '102': 0.4800, '1020': 1.0000, '1021': 5.0000, '1022': 0.1600, '1023': 0.0300,
            '1024': 0.7500, '1025': 0.2000, '1026': 0.0800, '1028': 0.1500, '1029': 0.0900,
            '103': 0.5000, '1030': 0.1100, '1031': 0.0500, '1032': 1.0000, '104': 0.6200,
            '1040': 0.5000, '105': 0.4500, '106': 0.8200, '107': 0.7500, '108': 0.6600,
            '109': 0.6000, '110': 0.5200, '111': 0.1000, '112': 0.8000, '113': 0.0100,
            '114': 0.3400, '115': 0.8000, '116': 0.7500, '117': 0.7000, '118': 0.6600,
            '119': 0.4500, '121': 0.0500, '122': 0.1100
        }
        
        for code, price in csv_prices.items():
            cursor.execute(
                "UPDATE materials SET price_per_pound = %s WHERE code = %s",
                (price, code)
            )
        
        print("Updated material prices from CSV data")
        
        # Create system settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id SERIAL PRIMARY KEY,
                key VARCHAR(100) UNIQUE NOT NULL,
                value TEXT,
                description VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Insert default camera settings
        cursor.execute("""
            INSERT INTO system_settings (key, value, description) 
            VALUES ('CAMERA_USERNAME', 'admin', 'Camera authentication username')
            ON CONFLICT (key) DO NOTHING;
        """)
        
        cursor.execute("""
            INSERT INTO system_settings (key, value, description) 
            VALUES ('CAMERA_PASSWORD', '', 'Camera authentication password')
            ON CONFLICT (key) DO NOTHING;
        """)
        
        print("Created system settings table")
        
        conn.commit()
        print("Database migration completed successfully")
        
    except Exception as e:
        print(f"Migration error: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate_database()