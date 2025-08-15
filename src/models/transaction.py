from decimal import Decimal
from datetime import datetime

class Transaction:
    def __init__(self, transaction_id, customer_id, transaction_type="BUY"):
        self.transaction_id = transaction_id
        self.customer_id = customer_id
        self.transaction_type = transaction_type  # BUY or SELL
        self.timestamp = datetime.now()
        self.items = []
        self.total_weight = Decimal('0')
        self.total_amount = Decimal('0')
        self.payment_method = ""
        self.status = "PENDING"

class TransactionItem:
    def __init__(self, metal_id, weight_pounds, price_per_pound):
        self.metal_id = metal_id
        self.weight_pounds = Decimal(str(weight_pounds))
        self.price_per_pound = Decimal(str(price_per_pound))
        self.total_value = self.weight_pounds * self.price_per_pound