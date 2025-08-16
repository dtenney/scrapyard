from app import db
from datetime import datetime
from decimal import Decimal

class Material(db.Model):
    __tablename__ = 'materials'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    description = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    is_ferrous = db.Column(db.Boolean, nullable=False, default=False)
    price_per_pound = db.Column(db.Numeric(10, 4), default=0.0000)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)