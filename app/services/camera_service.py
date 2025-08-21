import requests
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AxisCameraService:
    """Service for AXIS M2025-LE Network Camera"""
    
    def __init__(self, ip_address: str, username: str = None, password: str = None):
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
        
        # Use provided credentials or defaults
        self.username = username or 'admin'
        self.password = password or 'admin'
            
        self.base_url = f"http://{ip_address}"
        
    def get_stream_url(self, stream_path: str = "/axis-cgi/mjpg/video.cgi") -> str:
        """Get MJPEG stream URL with auth"""
        # Sanitize stream_path to prevent XSS
        import html
        safe_path = html.escape(stream_path)
        return f"http://{self.username}:{self.password}@{self.ip_address}{safe_path}?resolution=640x480&fps=15"
    
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
                logger.info("Image captured from %s", self.ip_address)
                return response.content
            else:
                logger.error(f"Failed to capture image: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error("Camera capture error: %s", str(e)[:100].replace('\n', ' ').replace('\r', ' '))
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
            safe_transaction_id = re.sub(r'[^a-zA-Z0-9_-]', '_', str(transaction_id)[:10])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"txn_{safe_transaction_id}_{safe_material}_{timestamp}.jpg"
            filepath = os.path.join(photo_dir, filename)
            
            # Validate path to prevent traversal
            if not os.path.abspath(filepath).startswith(os.path.abspath(photo_dir)):
                raise ValueError("Invalid file path")
            
            # Save image with error handling
            try:
                with open(filepath, 'wb') as f:
                    f.write(image_data)
            except (OSError, IOError, PermissionError) as e:
                logger.error("Failed to save photo: %s", str(e)[:100].replace('\n', ' ').replace('\r', ' '))
                return None
            
            logger.info("Transaction photo saved: %s", filename)
            return filename
        
        return None
    
    def test_connection(self) -> dict:
        """Test connection to camera and return stream info"""
        try:
            url = f"{self.base_url}/axis-cgi/param.cgi?action=list&group=Properties.System"
            
            response = requests.get(
                url,
                auth=(self.username, self.password),
                timeout=5
            )
            
            if response.status_code == 200:
                stream_url = self.get_stream_url()
                return {
                    'status': 'online', 
                    'message': 'Camera accessible - Live feed available',
                    'stream_url': stream_url,
                    'camera_type': 'AXIS',
                    'ip_address': self.ip_address
                }
            elif response.status_code == 401:
                return {'status': 'auth_error', 'message': 'Authentication required'}
            else:
                return {'status': 'error', 'message': f'HTTP {response.status_code}'}
                
        except Exception as e:
            logger.error("Camera connection test failed: %s", str(e)[:100].replace('\n', ' ').replace('\r', ' '))
            return {'status': 'offline', 'message': 'Connection failed'}
    
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
            logger.error("Error getting camera info: %s", str(e)[:100].replace('\n', ' ').replace('\r', ' '))
        
        return {}