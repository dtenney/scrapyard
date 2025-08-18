from app import db
from datetime import datetime

class CompetitivePrice(db.Model):
    __tablename__ = 'competitive_prices'
    
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    price_per_pound = db.Column(db.Numeric(10, 4), nullable=False)
    source = db.Column(db.String(50), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    material = db.relationship('Material', backref='competitive_prices')