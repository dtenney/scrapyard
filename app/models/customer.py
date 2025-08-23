from app import db
from datetime import datetime

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    street_address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(2))
    zip_code = db.Column(db.String(10))
    county = db.Column(db.String(100))

    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    drivers_license_number = db.Column(db.String(50))
    drivers_license_photo_path = db.Column(db.String(255))  # relative path to photo
    drivers_license_photo_filename = db.Column(db.String(100))  # original filename
    birthday = db.Column(db.Date)
    gender = db.Column(db.String(10))
    eye_color = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def full_address(self):
        """Return formatted full address"""
        parts = [self.street_address, self.city, self.state, self.zip_code]
        return ', '.join(filter(None, parts))
    
