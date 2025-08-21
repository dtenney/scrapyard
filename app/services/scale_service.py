from pymodbus.client import ModbusTcpClient
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class USRScaleService:
    """Service for USR-TCP232-410S with Modbus RTU to TCP conversion"""
    
    def __init__(self, ip_address: str, port: int = 502):
        self.ip_address = ip_address
        self.port = port
        self.client = None
        
    def connect(self) -> bool:
        """Connect to scale device via Modbus TCP"""
        try:
            self.client = ModbusTcpClient(self.ip_address, port=self.port)
            if self.client.connect():
                logger.info("Connected to scale via Modbus TCP")
                return True
            else:
                logger.error("Failed to connect to scale")
                return False
        except Exception as e:
            logger.error(f"Connection error: {str(e)[:100]}")
            return False
    
    def disconnect(self):
        """Disconnect from scale device"""
        if self.client:
            self.client.close()
            self.client = None
    
    def get_weight(self) -> Optional[float]:
        """Get current weight reading from scale"""
        if not self.client or not self.client.is_connected:
            if not self.connect():
                return None
        
        try:
            # Read holding registers (address 0, count 2 for 32-bit float)
            result = self.client.read_holding_registers(address=0, count=2, unit=1)
            
            if not result.isError():
                # Convert registers to float (implementation depends on scale)
                raw_value = (result.registers[0] << 16) | result.registers[1]
                weight = raw_value / 100.0  # Scale factor depends on device
                logger.debug(f"Weight reading: {weight}")
                return weight
            else:
                logger.warning("Error reading weight registers")
                return None
                
        except Exception as e:
            logger.error(f"Error reading weight: {str(e)[:100]}")
            self.disconnect()
            return None
    
    def tare_scale(self) -> bool:
        """Tare (zero) the scale"""
        if not self.client or not self.client.is_connected:
            if not self.connect():
                return False
        
        try:
            # Write tare command to coil (depends on scale)
            result = self.client.write_coil(address=0, value=True, unit=1)
            
            if not result.isError():
                logger.info("Tare command executed")
                return True
            else:
                logger.error("Error executing tare command")
                return False
                
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
                        'message': f'ModbusTCP Connected - Live Weight: {weight:.2f} lbs',
                        'weight': weight,
                        'connection_type': 'ModbusTCP',
                        'port': self.port
                    }
                else:
                    return {
                        'status': 'connected', 
                        'message': f'ModbusTCP Connected to {self.ip_address}:{self.port} but no weight data',
                        'connection_type': 'ModbusTCP',
                        'port': self.port
                    }
            else:
                return {
                    'status': 'offline', 
                    'message': f'ModbusTCP Connection failed to {self.ip_address}:{self.port}',
                    'connection_type': 'ModbusTCP',
                    'port': self.port
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'ModbusTCP Error: {str(e)[:100]}',
                'connection_type': 'ModbusTCP',
                'port': self.port
            }