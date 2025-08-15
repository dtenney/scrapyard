import sqlite3
import os

class Database:
    def __init__(self, db_path="scrapyard.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Metals table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metals (
                    metal_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    price_per_pound DECIMAL(10,4),
                    category TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Customers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT,
                    address TEXT,
                    id_number TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Transactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id INTEGER PRIMARY KEY,
                    customer_id INTEGER,
                    transaction_type TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_weight DECIMAL(10,4),
                    total_amount DECIMAL(10,2),
                    payment_method TEXT,
                    status TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
                )
            ''')
            
            # Transaction items table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transaction_items (
                    item_id INTEGER PRIMARY KEY,
                    transaction_id INTEGER,
                    metal_id INTEGER,
                    weight_pounds DECIMAL(10,4),
                    price_per_pound DECIMAL(10,4),
                    total_value DECIMAL(10,2),
                    FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id),
                    FOREIGN KEY (metal_id) REFERENCES metals (metal_id)
                )
            ''')
            
            conn.commit()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)