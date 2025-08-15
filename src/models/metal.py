from decimal import Decimal
from datetime import datetime

class Metal:
    def __init__(self, metal_id, name, price_per_pound, category=""):
        self.metal_id = metal_id
        self.name = name
        self.price_per_pound = Decimal(str(price_per_pound))
        self.category = category
        self.last_updated = datetime.now()

class MetalInventory:
    def __init__(self, metal_id, quantity_pounds, location=""):
        self.metal_id = metal_id
        self.quantity_pounds = Decimal(str(quantity_pounds))
        self.location = location
        self.last_updated = datetime.now()