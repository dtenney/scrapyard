import requests
import cv2
import base64
import logging
import os
import ipaddress
from datetime import datetime
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

class AxisCamera:
    """Driver for AXIS M2025-LE Network Camera"""
    
    def __init__(self, ip: str, username: str = None, password: str = None):
        # Validate IP address to prevent SSRF
        try:
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_loopback or ip_obj.is_private:
                # Allow private/loopback for legitimate camera networks
                pass
            elif not ip_obj.is_global:
                raise ValueError("Invalid IP address")
        except ValueError:
            raise ValueError(f"Invalid IP address: {ip}")
            
        self.ip = ip
        self.username = username or os.environ.get('CAMERA_USERNAME', 'admin')
        self.password = password or os.environ.get('CAMERA_PASSWORD', '')
        self.base_url = f"http://{ip}"
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.connected = False
    
    def connect(self) -> bool:
        """Test connection to camera"""
        try:
            response = self.session.get(f"{self.base_url}/axis-cgi/param.cgi?action=list&group=Properties.System")
            if response.status_code == 200:
                self.connected = True
                logger.info("Connected to AXIS camera at %s", self.ip)
                return True
        except Exception as e:
            logger.error("Failed to connect to camera: %s", str(e)[:100].replace('\n', ' ').replace('\r', ' '))
        
        self.connected = False
        return False
    
    def capture_image(self, resolution: str = "1920x1080") -> Optional[bytes]:
        """Capture a single image from the camera"""
        if not self.connected and not self.connect():
            return None
        
        try:
            url = f"{self.base_url}/axis-cgi/jpg/image.cgi"
            params = {
                'resolution': resolution,
                'compression': 50
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            try:
                if response.status_code == 200:
                    logger.info("Image captured from camera %s", self.ip)
                    return response.content
                else:
                    logger.error("Failed to capture image: HTTP %d", response.status_code)
            finally:
                response.close()
                
        except Exception as e:
            logger.error("Error capturing image: %s", str(e)[:100].replace('\n', ' ').replace('\r', ' '))
        
        return None
    
    def get_mjpeg_stream_url(self) -> str:
        """Get MJPEG stream URL for live video"""
        return f"{self.base_url}/axis-cgi/mjpg/video.cgi?resolution=640x480&fps=15"
    
    def start_recording(self, duration: int = 30) -> bool:
        """Start recording video (if supported)"""
        try:
            url = f"{self.base_url}/axis-cgi/record/record.cgi"
            params = {
                'diskid': 'SD_DISK',
                'duration': duration
            }
            
            response = self.session.post(url, params=params, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error("Error starting recording: %s", str(e)[:100].replace('\n', ' ').replace('\r', ' '))
            return False
    
    def get_camera_info(self) -> dict:
        """Get camera information and capabilities"""
        if not self.connected and not self.connect():
            return {}
        
        try:
            # Get basic properties
            response = self.session.get(f"{self.base_url}/axis-cgi/param.cgi?action=list&group=Properties")
            
            if response.status_code == 200:
                info = {
                    'ip': self.ip,
                    'connected': True,
                    'model': 'AXIS M2025-LE',
                    'stream_url': self.get_mjpeg_stream_url()
                }
                
                # Parse response for additional info
                for line in response.text.split('\n'):
                    if 'ProdNbr' in line:
                        info['product_number'] = line.split('=')[1]
                    elif 'SerialNumber' in line:
                        info['serial_number'] = line.split('=')[1]
                    elif 'Version' in line:
                        info['firmware_version'] = line.split('=')[1]
                
                return info
                
        except Exception as e:
            logger.error("Error getting camera info: %s", str(e)[:100].replace('\n', ' ').replace('\r', ' '))
        
        return {'ip': self.ip, 'connected': False}
    
    def set_preset(self, preset_name: str, position: dict) -> bool:
        """Set a camera preset position (if PTZ supported)"""
        try:
            url = f"{self.base_url}/axis-cgi/com/ptz.cgi"
            params = {
                'setserverpresetname': preset_name,
                'pan': position.get('pan', 0),
                'tilt': position.get('tilt', 0),
                'zoom': position.get('zoom', 1)
            }
            
            response = self.session.get(url, params=params)
            return response.status_code == 200
            
        except Exception as e:
            logger.error("Error setting preset: %s", str(e)[:100].replace('\n', ' ').replace('\r', ' '))
            return False
    
    def goto_preset(self, preset_name: str) -> bool:
        """Move camera to preset position"""
        try:
            url = f"{self.base_url}/axis-cgi/com/ptz.cgi"
            params = {'gotoserverpresetname': preset_name}
            
            response = self.session.get(url, params=params)
            return response.status_code == 200
            
        except Exception as e:
            logger.error("Error going to preset: %s", str(e)[:100].replace('\n', ' ').replace('\r', ' '))
            return False
    
    def capture_scale_photo(self, transaction_id: str) -> Optional[str]:
        """Capture photo of items on scale and return base64 encoded image"""
        image_data = self.capture_image()
        
        if image_data:
            # Convert to base64 for storage/transmission
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Sanitize transaction_id to prevent path traversal
            safe_transaction_id = ''.join(c for c in str(transaction_id) if c.isalnum() or c in '-_')
            filename = f"scale_photo_{safe_transaction_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            
            try:
                photo_dir = "/var/www/scrapyard/photos"
                os.makedirs(photo_dir, exist_ok=True)
                filepath = os.path.join(photo_dir, filename)
                
                # Ensure path is within allowed directory
                if not os.path.abspath(filepath).startswith(os.path.abspath(photo_dir)):
                    raise ValueError("Invalid file path")
                    
                with open(filepath, 'wb') as f:
                    f.write(image_data)
                logger.info("Scale photo saved: %s", filename)
            except Exception as e:
                logger.error("Error saving photo: %s", str(e)[:100].replace('\n', ' ').replace('\r', ' '))
            
            return base64_image
        
        return None