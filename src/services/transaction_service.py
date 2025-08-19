from decimal import Decimal
from ..models.transaction import Transaction, TransactionItem
from .database import Database

class TransactionService:
    def __init__(self):
        self.db = Database()
    
    def create_transaction(self, customer_id, transaction_type="BUY"):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transactions (customer_id, transaction_type, status)
                VALUES (?, ?, ?)
            ''', (customer_id, transaction_type, "PENDING"))
            return cursor.lastrowid
    
    def add_item_to_transaction(self, transaction_id, metal_id, weight_pounds, price_per_pound):
        if weight_pounds is None or price_per_pound is None:
            raise ValueError("Weight and price cannot be None")
        total_value = Decimal(str(weight_pounds)) * Decimal(str(price_per_pound))
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transaction_items (transaction_id, metal_id, weight_pounds, price_per_pound, total_value)
                VALUES (?, ?, ?, ?, ?)
            ''', (transaction_id, metal_id, weight_pounds, price_per_pound, float(total_value)))
            conn.commit()
    
    def complete_transaction(self, transaction_id, payment_method):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Calculate totals
            cursor.execute('''
                SELECT SUM(weight_pounds), SUM(total_value)
                FROM transaction_items
                WHERE transaction_id = ?
            ''', (transaction_id,))
            
            result = cursor.fetchone()
            if result is None:
                raise ValueError("No transaction items found")
            total_weight, total_amount = result
            
            # Update transaction
            cursor.execute('''
                UPDATE transactions
                SET total_weight = ?, total_amount = ?, payment_method = ?, status = ?
                WHERE transaction_id = ?
            ''', (total_weight, total_amount, payment_method, "COMPLETED", transaction_id))
            
            conn.commit()
            return total_amount