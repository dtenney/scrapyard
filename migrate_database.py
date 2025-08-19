#!/usr/bin/env python3
"""
Database migration script to update existing tables with new columns
"""

import psycopg2
from config.settings import Config

def migrate_database():
    """Add missing columns to existing tables"""
    
    # Parse database URL
    db_url = Config.SQLALCHEMY_DATABASE_URI
    # Extract connection details from postgresql://user:pass@host:port/db
    parts = db_url.replace('postgresql://', '').split('@')
    user_pass = parts[0].split(':')
    host_port_db = parts[1].split('/')
    host_port = host_port_db[0].split(':')
    
    conn = psycopg2.connect(
        host=host_port[0],
        port=int(host_port[1]) if len(host_port) > 1 else 5432,
        database=host_port_db[1],
        user=user_pass[0],
        password=user_pass[1] if len(user_pass) > 1 else ''
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
        
        conn.commit()
        print("Database migration completed successfully")
        
    except Exception as e:
        print(f"Migration error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    migrate_database()