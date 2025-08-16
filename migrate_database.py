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