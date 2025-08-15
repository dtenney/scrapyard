import socket
import threading
import time
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class USRScaleReader:
    """Driver for USR-TCP232-410S Serial-to-Ethernet converter connected to weight scales"""
    
    def __init__(self, ip: str, port: int = 8899, timeout: int = 5):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.connected = False
        self.weight = 0.0
        self.stable = False
        self.unit = "lbs"
        self.callback = None
        self.running = False
        self.thread = None
    
    def connect(self) -> bool:
        """Connect to the scale via TCP"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.ip, self.port))
            self.connected = True
            logger.info(f"Connected to scale at {self.ip}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to scale: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the scale"""
        self.running = False
        if self.thread:
            self.thread.join()
        if self.socket:
            self.socket.close()
        self.connected = False
        logger.info("Disconnected from scale")
    
    def start_reading(self, callback: Optional[Callable] = None):
        """Start continuous weight reading in a separate thread"""
        if not self.connected:
            if not self.connect():
                return False
        
        self.callback = callback
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        return True
    
    def _read_loop(self):
        """Continuous reading loop"""
        while self.running and self.connected:
            try:
                # Send weight request command
                self.socket.send(b'W\r\n')
                
                # Read response
                data = self.socket.recv(1024).decode('ascii').strip()
                
                # Parse weight data (format varies by scale manufacturer)
                weight_data = self._parse_weight_data(data)
                
                if weight_data:
                    self.weight = weight_data['weight']
                    self.stable = weight_data['stable']
                    self.unit = weight_data['unit']
                    
                    if self.callback:
                        self.callback(weight_data)
                
                time.sleep(0.1)  # 10Hz reading rate
                
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error reading from scale: {e}")
                self.connected = False
                break
    
    def _parse_weight_data(self, data: str) -> Optional[dict]:
        """Parse weight data from scale response"""
        try:
            # Example format: "ST,GS,+00012.34,lb"
            # ST = stable, US = unstable
            # GS = gross weight, NT = net weight
            parts = data.split(',')
            
            if len(parts) >= 4:
                stable = parts[0] == 'ST'
                weight_str = parts[2]
                unit = parts[3]
                
                # Remove + sign and convert to float
                weight = float(weight_str.replace('+', ''))
                
                return {
                    'weight': weight,
                    'stable': stable,
                    'unit': unit,
                    'raw_data': data
                }
        except Exception as e:
            logger.error(f"Error parsing weight data: {e}")
        
        return None
    
    def get_current_weight(self) -> dict:
        """Get current weight reading"""
        return {
            'weight': self.weight,
            'stable': self.stable,
            'unit': self.unit,
            'connected': self.connected
        }
    
    def tare(self) -> bool:
        """Send tare command to zero the scale"""
        if not self.connected:
            return False
        
        try:
            self.socket.send(b'T\r\n')
            return True
        except Exception as e:
            logger.error(f"Error sending tare command: {e}")
            return False