from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config.settings import Config
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login_get'
    
    from app.models.user import User
    
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except (ValueError, TypeError):
            return None
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.cashier import cashier_bp
    from app.routes.photo import photo_bp
    from app.routes.receipt_templates import receipt_templates_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(cashier_bp, url_prefix='/cashier')
    app.register_blueprint(photo_bp)
    app.register_blueprint(receipt_templates_bp, url_prefix='/admin/receipt_templates')
    
    # Initialize services on startup
    with app.app_context():
        try:
            from app.services.startup_service import initialize_virtual_serial_devices
            from app.services.photo_service import PhotoService
            initialize_virtual_serial_devices()
            PhotoService.init_upload_directory()
        except Exception as e:
            app.logger.error(f"Failed to initialize services: {e}")
    
    return app