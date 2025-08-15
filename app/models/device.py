from app import db
from datetime import datetime

class Device(db.Model):
    __tablename__ = 'devices'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)  # scale, printer, camera, scanner
    ip_address = db.Column(db.String(15))
    port = db.Column(db.Integer)
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    group_id = db.Column(db.Integer, db.ForeignKey('user_groups.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime)
    
    # Configuration JSON field
    config = db.Column(db.JSON)
    
    # Relationships
    group = db.relationship('UserGroup', back_populates='devices')

class Scale(db.Model):
    __tablename__ = 'scales'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    capacity = db.Column(db.Float)  # Maximum weight capacity
    precision = db.Column(db.Float, default=0.01)  # Weight precision
    unit = db.Column(db.String(10), default='lbs')
    calibration_date = db.Column(db.DateTime)
    
    device = db.relationship('Device', backref='scale_config')

class Printer(db.Model):
    __tablename__ = 'printers'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    printer_type = db.Column(db.String(50))  # thermal, laser, inkjet
    paper_width = db.Column(db.Float)
    dpi = db.Column(db.Integer, default=203)
    
    device = db.relationship('Device', backref='printer_config')

class Camera(db.Model):
    __tablename__ = 'cameras'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    resolution = db.Column(db.String(20))  # 1920x1080
    fps = db.Column(db.Integer, default=30)
    stream_url = db.Column(db.String(255))
    
    device = db.relationship('Device', backref='camera_config')