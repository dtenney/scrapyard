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
        
        print("Added missing columns to devices table")
        
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