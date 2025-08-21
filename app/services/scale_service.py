import serial
import logging
import re
import time
from typing import Optional

logger = logging.getLogger(__name__)

class USRScaleService:
    """Service for scale devices via virtual serial connection using socat"""
    
    def __init__(self, serial_port: str, baud_rate: int = 9600, data_bits: int = 8, 
                 parity: str = 'N', stop_bits: int = 1, flow_control: str = 'none'):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.data_bits = data_bits
        self.parity = parity.upper()
        self.stop_bits = stop_bits
        self.flow_control = flow_control.lower()
        self.connection = None
        
    def connect(self) -> bool:
        """Connect to scale device via serial"""
        try:
            # Map parity settings
            parity_map = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
            
            # Map flow control settings
            xonxoff = self.flow_control == 'xonxoff'
            rtscts = self.flow_control == 'rtscts'
            
            self.connection = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                bytesize=self.data_bits,
                parity=parity_map.get(self.parity, serial.PARITY_NONE),
                stopbits=self.stop_bits,
                timeout=2,
                xonxoff=xonxoff,
                rtscts=rtscts
            )
            
            logger.info(f"Connected to scale at {self.serial_port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to scale: {str(e)[:100]}")
            return False
    
    def disconnect(self):
        """Disconnect from scale device"""
        if self.connection and self.connection.is_open:
            self.connection.close()
            self.connection = None
    
    def get_weight(self) -> Optional[float]:
        """Get current weight reading from scale"""
        if not self.connection or not self.connection.is_open:
            if not self.connect():
                return None
        
        try:
            # Send weight request command (common commands: 'W\r\n', 'P\r\n', or just read continuously)
            self.connection.write(b'W\r\n')
            time.sleep(0.1)
            
            # Read response
            response = self.connection.readline().decode('ascii', errors='ignore').strip()
            
            # Parse weight from response using regex
            # Common formats: "W 123.45 lb", "123.45", "ST,GS,+123.45,lb"
            weight_patterns = [
                r'([+-]?\d+\.?\d*)\s*(?:lb|kg|g)?',  # Simple number with optional unit
                r'ST,GS,([+-]?\d+\.?\d*),',          # Toledo format
                r'W\s+([+-]?\d+\.?\d*)',             # W command response
            ]
            
            for pattern in weight_patterns:
                match = re.search(pattern, response)
                if match:
                    weight = float(match.group(1))
                    logger.debug(f"Weight reading: {weight}")
                    return weight
            
            logger.warning(f"Could not parse weight from response: {response}")
            return None
                
        except Exception as e:
            logger.error(f"Error reading weight: {str(e)[:100]}")
            self.disconnect()
            return None
    
    def tare_scale(self) -> bool:
        """Tare (zero) the scale"""
        if not self.connection or not self.connection.is_open:
            if not self.connect():
                return False
        
        try:
            # Send tare command (common commands: 'T\r\n', 'Z\r\n')
            self.connection.write(b'T\r\n')
            time.sleep(0.5)
            
            response = self.connection.readline().decode('ascii', errors='ignore').strip()
            logger.info(f"Tare command executed, response: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Error taring scale: {str(e)[:100]}")
            self.disconnect()
            return False
    
    def test_connection(self) -> dict:
        """Test connection to scale device with live weight reading"""
        try:
            if self.connect():
                weight = self.get_weight()
                self.disconnect()
                
                if weight is not None:
                    return {
                        'status': 'online', 
                        'message': f'Serial Connected - Live Weight: {weight:.2f} lbs',
                        'weight': weight,
                        'connection_type': 'Serial',
                        'port': self.serial_port,
                        'baud_rate': self.baud_rate,
                        'config': f'{self.data_bits}{self.parity}{self.stop_bits}'
                    }
                else:
                    return {
                        'status': 'connected', 
                        'message': f'Serial Connected to {self.serial_port} but no weight data',
                        'connection_type': 'Serial',
                        'port': self.serial_port,
                        'baud_rate': self.baud_rate,
                        'config': f'{self.data_bits}{self.parity}{self.stop_bits}'
                    }
            else:
                return {
                    'status': 'offline', 
                    'message': f'Serial Connection failed to {self.serial_port}',
                    'connection_type': 'Serial',
                    'port': self.serial_port,
                    'baud_rate': self.baud_rate,
                    'config': f'{self.data_bits}{self.parity}{self.stop_bits}'
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Serial Error: {str(e)[:100]}',
                'connection_type': 'Serial',
                'port': self.serial_port
            }