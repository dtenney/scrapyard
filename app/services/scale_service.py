import socket
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class USRScaleService:
    """Service for USR-TCP232-410S serial to ethernet scale devices"""
    
    def __init__(self, ip_address: str, port: int = 23):
        self.ip_address = ip_address
        self.port = port
        self.socket = None
        
    def connect(self) -> bool:
        """Connect to scale device"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.ip_address, self.port))
            logger.info("Connected to scale successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to scale: {str(e)[:100]}")
            return False
    
    def disconnect(self):
        """Disconnect from scale device"""
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def get_weight(self) -> Optional[float]:
        """Get current weight reading from scale"""
        if not self.socket:
            if not self.connect():
                return None
        
        try:
            # Send weight request command (varies by scale manufacturer)
            self.socket.send(b'W\\r\\n')  # Common weight request command
            
            # Read response
            response = self.socket.recv(1024).decode('ascii').strip()
            
            # Parse weight from response (format varies by scale)
            # Common formats: "W 123.45 lb" or "123.45"
            import re
            weight_match = re.search(r'([+-]?\\d+\\.?\\d*)', response)
            
            if weight_match:
                weight = float(weight_match.group(1))
                logger.debug("Weight reading obtained")
                return weight
            else:
                logger.warning("Could not parse weight from response")
                return None
                
        except Exception as e:
            logger.error("Error reading weight")
            self.disconnect()
            return None
    
    def tare_scale(self) -> bool:
        """Tare (zero) the scale"""
        if not self.socket:
            if not self.connect():
                return False
        
        try:
            self.socket.send(b'T\\r\\n')  # Common tare command
            response = self.socket.recv(1024).decode('ascii').strip()
            logger.info("Tare command executed")
            return True
        except Exception as e:
            logger.error("Error taring scale")
            self.disconnect()
            return False
    
    def test_connection(self) -> dict:
        """Test connection to scale device"""
        if self.connect():
            weight = self.get_weight()
            self.disconnect()
            
            if weight is not None:
                return {'status': 'online', 'weight': weight}
            else:
                return {'status': 'connected', 'message': 'Connected but no weight data'}
        else:
            return {'status': 'offline', 'message': 'Connection failed'}