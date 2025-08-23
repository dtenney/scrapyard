from app import db
from datetime import datetime

class ReceiptTemplate(db.Model):
    __tablename__ = 'receipt_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    header_logo_path = db.Column(db.String(255))
    company_name = db.Column(db.String(100))
    company_address = db.Column(db.Text)
    footer_text = db.Column(db.Text)
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ReceiptTemplate {self.name}>'