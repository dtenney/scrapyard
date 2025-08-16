import socket
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class StarPrinterService:
    """Service for Star Micronics thermal label printers"""
    
    def __init__(self, ip_address: str, port: int = 9100):
        self.ip_address = ip_address
        self.port = port
        
    def print_receipt(self, content: str, printer_model: str = "TSP143III") -> bool:
        """Print receipt content to Star Micronics printer"""
        try:
            # Connect to printer
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.ip_address, self.port))
            
            # Star printer ESC/POS commands
            commands = []
            
            # Initialize printer
            commands.append(b'\\x1B\\x40')  # ESC @ - Initialize
            
            # Set font and alignment
            commands.append(b'\\x1B\\x61\\x01')  # ESC a 1 - Center align
            commands.append(b'\\x1B\\x21\\x08')  # ESC ! 8 - Double height
            
            # Print header
            commands.append(b'ARMOR METALS RECEIPT\\n\\n')
            
            # Reset to normal
            commands.append(b'\\x1B\\x21\\x00')  # ESC ! 0 - Normal
            commands.append(b'\\x1B\\x61\\x00')  # ESC a 0 - Left align
            
            # Print content
            commands.append(content.encode('utf-8'))
            commands.append(b'\\n\\n')
            
            # Cut paper (if supported)
            if printer_model in ["TSP143III", "TSP654II"]:
                commands.append(b'\\x1D\\x56\\x41')  # GS V A - Full cut
            
            # Send all commands
            for cmd in commands:
                sock.send(cmd)
            
            sock.close()
            logger.info(f"Receipt printed to {self.ip_address}")
            return True
            
        except Exception as e:
            logger.error(f"Print error: {e}")
            return False
    
    def print_label(self, material: str, weight: float, price: float, customer: str) -> bool:
        """Print scrap metal label"""
        content = f"""
Material: {material}
Weight: {weight:.2f} lbs
Price: ${price:.2f}
Customer: {customer}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """.strip()
        
        return self.print_receipt(content)
    
    def test_connection(self) -> dict:
        """Test connection to printer"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.ip_address, self.port))
            
            # Send status request
            sock.send(b'\\x10\\x04\\x01')  # DLE EOT 1 - Real-time status
            
            sock.close()
            return {'status': 'online', 'message': 'Printer ready'}
            
        except Exception as e:
            return {'status': 'offline', 'message': str(e)}