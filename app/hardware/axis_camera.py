import requests
import cv2
import base64
import logging
from datetime import datetime
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

class AxisCamera:
    """Driver for AXIS M2025-LE Network Camera"""
    
    def __init__(self, ip: str, username: str = 'admin', password: str = 'admin'):
        self.ip = ip
        self.username = username
        self.password = password
        self.base_url = f"http://{ip}"
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.connected = False
    
    def connect(self) -> bool:
        """Test connection to camera"""
        try:
            response = self.session.get(f"{self.base_url}/axis-cgi/param.cgi?action=list&group=Properties.System")
            if response.status_code == 200:
                self.connected = True
                logger.info(f"Connected to AXIS camera at {self.ip}")
                return True
        except Exception as e:
            logger.error(f"Failed to connect to camera: {e}")
        
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
            
            if response.status_code == 200:
                logger.info(f"Image captured from camera {self.ip}")
                return response.content
            else:
                logger.error(f"Failed to capture image: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error capturing image: {e}")
        
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
            
            response = self.session.post(url, params=params)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
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
            logger.error(f"Error getting camera info: {e}")
        
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
            logger.error(f"Error setting preset: {e}")
            return False
    
    def goto_preset(self, preset_name: str) -> bool:
        """Move camera to preset position"""
        try:
            url = f"{self.base_url}/axis-cgi/com/ptz.cgi"
            params = {'gotoserverpresetname': preset_name}
            
            response = self.session.get(url, params=params)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error going to preset: {e}")
            return False
    
    def capture_scale_photo(self, transaction_id: str) -> Optional[str]:
        """Capture photo of items on scale and return base64 encoded image"""
        image_data = self.capture_image()
        
        if image_data:
            # Convert to base64 for storage/transmission
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Optionally save to file
            filename = f"scale_photo_{transaction_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            
            try:
                with open(f"/var/www/scrapyard/photos/{filename}", 'wb') as f:
                    f.write(image_data)
                logger.info(f"Scale photo saved: {filename}")
            except Exception as e:
                logger.error(f"Error saving photo: {e}")
            
            return base64_image
        
        return None