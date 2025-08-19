#!/usr/bin/env python3
"""
Migrate customer addresses to new field structure
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate_addresses():
    """Run the address field migration"""
    try:
        # Get database connection from environment or default
        db_url = os.getenv('DATABASE_URL', 'postgresql://scrapyard:scrapyard@localhost/scrapyard')
        
        # Parse connection string
        if db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', '')
        
        parts = db_url.split('@')
        if len(parts) == 2:
            user_pass, host_db = parts
            user, password = user_pass.split(':')
            host, database = host_db.split('/')
        else:
            print("Invalid DATABASE_URL format")
            return False
        
        # Connect to database
        with psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password
        ) as conn:
            cursor = conn.cursor()
            
            # Read and execute migration SQL
            try:
                with open('add_customer_address_fields.sql', 'r') as f:
                    migration_sql = f.read()
            except FileNotFoundError:
                print("✗ Migration SQL file not found: add_customer_address_fields.sql")
                return False
            
            cursor.execute(migration_sql)
            conn.commit()
            
            print("✓ Customer address fields migration completed successfully")
            cursor.close()
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False

if __name__ == '__main__':
    success = migrate_addresses()
    sys.exit(0 if success else 1)