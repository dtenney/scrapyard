from datetime import datetime

class Customer:
    def __init__(self, customer_id, name, phone="", address="", id_number=""):
        self.customer_id = customer_id
        self.name = name
        self.phone = phone
        self.address = address
        self.id_number = id_number  # For compliance tracking
        self.created_date = datetime.now()
        self.total_transactions = 0
        self.total_value = 0.0