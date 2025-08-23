import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class PhotoService:
    """Service for handling customer photo uploads and storage"""
    
    UPLOAD_FOLDER = '/var/www/scrapyard/uploads/customer_photos'
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    @classmethod
    def init_upload_directory(cls):
        """Create upload directory structure if it doesn't exist"""
        try:
            # Create customer photos directory with 775 permissions
            os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
            os.chmod(cls.UPLOAD_FOLDER, 0o775)
            
            # Create logos directory with 775 permissions
            logo_dir = '/var/www/scrapyard/uploads/logos'
            os.makedirs(logo_dir, exist_ok=True)
            os.chmod(logo_dir, 0o775)
            
            logger.info(f"Upload directories initialized with 775 permissions")
            return True
        except Exception as e:
            logger.error(f"Failed to create upload directory: {e}")
            return False
    
    @classmethod
    def allowed_file(cls, filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in cls.ALLOWED_EXTENSIONS
    
    @classmethod
    def save_customer_photo(cls, customer_id, file):
        """Save customer driver's license photo"""
        if not file or not cls.allowed_file(file.filename):
            return None, "Invalid file type"
        
        # Create date-based directory structure
        now = datetime.now()
        date_path = f"{now.year}/{now.month:02d}"
        full_dir = os.path.join(cls.UPLOAD_FOLDER, date_path)
        
        try:
            os.makedirs(full_dir, exist_ok=True)
            os.chmod(full_dir, 0o775)
        except Exception as e:
            logger.error(f"Failed to create directory: {str(e)[:100]}")
            return None, "Failed to create storage directory"
        
        # Generate unique filename
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"customer_{customer_id}_dl_{timestamp}.{file_ext}"
        
        # Full file path
        file_path = os.path.join(full_dir, filename)
        relative_path = os.path.join(date_path, filename)
        
        try:
            file.save(file_path)
            # Set proper permissions
            os.chmod(file_path, 0o644)
            logger.info(f"Saved customer photo: {relative_path.replace('..', '').replace('/', '_')}")
            return relative_path, None
        except Exception as e:
            logger.error(f"Failed to save photo: {str(e)[:100]}")
            return None, "Failed to save photo"
    
    @classmethod
    def get_photo_path(cls, relative_path):
        """Get full filesystem path from relative path"""
        if not relative_path:
            return None
        # Prevent path traversal attacks
        if '..' in relative_path or relative_path.startswith('/'):
            return None
        return os.path.join(cls.UPLOAD_FOLDER, relative_path)
    
    @classmethod
    def save_receipt_logo(cls, file):
        """Save receipt template logo in uploads/logos directory"""
        if not file or not file.filename.lower().endswith(('.jpg', '.jpeg')):
            return {'success': False, 'error': 'Only JPG files allowed'}
        
        # Use dedicated logos directory with proper permissions
        logo_dir = '/var/www/scrapyard/uploads/logos'
        
        try:
            os.makedirs(logo_dir, exist_ok=True)
            os.chmod(logo_dir, 0o775)
        except Exception as e:
            logger.error(f"Failed to create logo directory: {e}")
            return {'success': False, 'error': 'Failed to create directory'}
        
        # Generate unique filename
        filename = f"logo_{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(logo_dir, filename)
        
        try:
            file.save(filepath)
            os.chmod(filepath, 0o664)
            logger.info(f"Saved receipt logo: {filename}")
            return {'success': True, 'filename': filename}
        except Exception as e:
            logger.error(f"Failed to save logo: {e}")
            return {'success': False, 'error': 'Failed to save logo'}
    
    @classmethod
    def delete_photo(cls, relative_path):
        """Delete photo file from filesystem"""
        if not relative_path:
            return True
        
        full_path = cls.get_photo_path(relative_path)
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"Deleted photo: {relative_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete photo {relative_path}: {e}")
            return False