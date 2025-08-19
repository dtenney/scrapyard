import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://scrapyard:scrapyard123@localhost/scrapyard_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File uploads
    UPLOAD_FOLDER = '/var/www/scrapyard/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Hardware defaults
    DEFAULT_SCALE_PORT = 8899
    DEFAULT_PRINTER_PORT = 9100
    DEFAULT_CAMERA_PORT = 80
    
    # Compliance
    NJ_LICENSE_NUMBER = os.environ.get('NJ_LICENSE_NUMBER', 'REQUIRED')
    REQUIRE_CUSTOMER_ID = True
    PHOTO_REQUIRED = True
    
    # Redis for caching
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'