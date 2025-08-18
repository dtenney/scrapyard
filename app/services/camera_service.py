import requests
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AxisCameraService:
    """Service for AXIS M2025-LE Network Camera"""
    
    def __init__(self, ip_address: str, username: str = "root", password: str = ""):
        import ipaddress
        # Validate IP address to prevent SSRF
        try:
            ip = ipaddress.ip_address(ip_address)
            if ip.is_private or ip.is_loopback:
                # Allow private/local IPs for legitimate camera access
                pass
            elif not ip.is_global:
                raise ValueError("Invalid IP address")
        except ValueError:
            raise ValueError(f"Invalid IP address: {ip_address}")
        
        self.ip_address = ip_address
        self.username = username
        self.password = password or "admin"  # Use environment variable in production
        self.base_url = f"http://{ip_address}"
        
    def get_stream_url(self, stream_path: str = "/axis-cgi/mjpg/video.cgi") -> str:
        """Get MJPEG stream URL"""
        return f"{self.base_url}{stream_path}?resolution=640x480&fps=15"
    
    def capture_image(self) -> Optional[bytes]:
        """Capture single image from camera"""
        try:
            url = f"{self.base_url}/axis-cgi/jpg/image.cgi?resolution=1280x720"
            
            response = requests.get(
                url,
                auth=(self.username, self.password),
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Image captured from {self.ip_address}")
                return response.content
            else:
                logger.error(f"Failed to capture image: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error("Camera capture error occurred")
            return None
    
    def save_transaction_photo(self, transaction_id: int, material: str) -> Optional[str]:
        """Capture and save photo for transaction"""
        image_data = self.capture_image()
        
        if image_data:
            import os
            from datetime import datetime
            
            # Create photos directory
            photo_dir = "/var/www/scrapyard/static/photos"
            os.makedirs(photo_dir, exist_ok=True)
            
            # Generate secure filename
            import re
            safe_material = re.sub(r'[^a-zA-Z0-9_-]', '_', str(material)[:20])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"txn_{transaction_id}_{safe_material}_{timestamp}.jpg"
            filepath = os.path.join(photo_dir, filename)
            
            # Validate path to prevent traversal
            if not filepath.startswith(photo_dir):
                raise ValueError("Invalid file path")
            
            # Save image
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            logger.info("Transaction photo saved successfully")
            return filename
        
        return None
    
    def test_connection(self) -> dict:
        """Test connection to camera"""
        try:
            url = f"{self.base_url}/axis-cgi/param.cgi?action=list&group=Properties.System"
            
            response = requests.get(
                url,
                auth=(self.username, self.password),
                timeout=5
            )
            
            if response.status_code == 200:
                return {'status': 'online', 'message': 'Camera accessible'}
            elif response.status_code == 401:
                return {'status': 'auth_error', 'message': 'Authentication required'}
            else:
                return {'status': 'error', 'message': f'HTTP {response.status_code}'}
                
        except Exception as e:
            return {'status': 'offline', 'message': str(e)}
    
    def get_camera_info(self) -> dict:
        """Get camera model and firmware info"""
        try:
            url = f"{self.base_url}/axis-cgi/param.cgi?action=list&group=Properties"
            
            response = requests.get(
                url,
                auth=(self.username, self.password),
                timeout=5
            )
            
            if response.status_code == 200:
                info = {}
                for line in response.text.split('\\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        if 'ProductFullName' in key:
                            info['model'] = value
                        elif 'Version' in key:
                            info['firmware'] = value
                
                return info
            
        except Exception as e:
            logger.error(f"Error getting camera info: {e}")
        
        return {}