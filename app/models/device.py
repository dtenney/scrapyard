from app import db
from datetime import datetime

class Device(db.Model):
    __tablename__ = 'devices'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(20), nullable=False)  # scale, printer, camera
    ip_address = db.Column(db.String(15), nullable=False)
    
    # Scale-specific fields
    serial_port = db.Column(db.String(50))  # Virtual serial device path
    baud_rate = db.Column(db.Integer, default=9600)
    data_bits = db.Column(db.Integer, default=8)
    parity = db.Column(db.String(10), default='N')  # N, E, O
    stop_bits = db.Column(db.Integer, default=1)
    flow_control = db.Column(db.String(10), default='none')  # none, xonxoff, rtscts
    
    # Printer-specific fields
    printer_model = db.Column(db.String(50))
    
    # Camera-specific fields
    camera_model = db.Column(db.String(50))
    stream_url = db.Column(db.String(200))
    camera_username = db.Column(db.String(50))
    camera_password = db.Column(db.String(100))
    
    is_active = db.Column(db.Boolean, default=True)
    last_seen = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)