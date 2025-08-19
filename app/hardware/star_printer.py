import socket
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class StarMicronicsPrinter:
    """Driver for Star Micronics thermal label printers"""
    
    def __init__(self, ip: str, port: int = 9100):
        self.ip = ip
        self.port = port
        self.socket = None
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to the printer via TCP"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.ip, self.port))
            self.connected = True
            logger.info(f"Connected to Star printer at {self.ip}:{self.port}")
            return True
        except (socket.error, socket.timeout, ConnectionRefusedError) as e:
            logger.error("Failed to connect to printer: %s", str(e)[:100].replace('\n', ' ').replace('\r', ' '))
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
    
    def disconnect(self):
        """Disconnect from the printer"""
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.socket.close()
        self.connected = False
    
    def print_receipt(self, transaction_data: dict) -> bool:
        """Print a scrap receipt"""
        if not self.connected and not self.connect():
            return False
        
        try:
            # ESC/POS commands for Star printers
            commands = []
            
            # Initialize printer
            commands.append(b'\x1b\x40')  # ESC @
            
            # Set font size and alignment
            commands.append(b'\x1b\x21\x30')  # Double height/width
            commands.append(b'\x1b\x61\x01')  # Center alignment
            
            # Header
            commands.append(b'SCRAP RECEIPT\n')
            commands.append(b'\x1b\x21\x00')  # Normal size
            commands.append(b'=' * 32 + b'\n')
            
            # Transaction details
            commands.append(b'\x1b\x61\x00')  # Left alignment
            commands.append(f"Date: {datetime.now().strftime('%m/%d/%Y %H:%M')}\n".encode())
            commands.append(f"Transaction: {transaction_data.get('id', 'N/A')}\n".encode())
            commands.append(f"Customer: {transaction_data.get('customer_name', 'N/A')}\n".encode())
            commands.append(b'-' * 32 + b'\n')
            
            # Items
            for item in transaction_data.get('items', []):
                metal_type = item.get('metal_type', 'Unknown')
                weight = item.get('weight', 0)
                price = item.get('price_per_lb', 0)
                total = item.get('total', 0)
                
                commands.append(f"{metal_type}\n".encode())
                commands.append(f"  {weight:.2f} lbs @ ${price:.2f}/lb\n".encode())
                commands.append(f"  Total: ${total:.2f}\n".encode())
            
            commands.append(b'-' * 32 + b'\n')
            
            # Total
            total_weight = transaction_data.get('total_weight', 0)
            total_amount = transaction_data.get('total_amount', 0)
            
            commands.append(f"Total Weight: {total_weight:.2f} lbs\n".encode())
            commands.append(b'\x1b\x21\x10')  # Double width
            commands.append(f"TOTAL: ${total_amount:.2f}\n".encode())
            commands.append(b'\x1b\x21\x00')  # Normal size
            
            # Footer
            commands.append(b'\n')
            commands.append(b'\x1b\x61\x01')  # Center alignment
            commands.append(b'Thank you for your business!\n')
            commands.append(b'NJ License: 12345\n')
            
            # Cut paper
            commands.append(b'\x1b\x64\x03')  # Feed 3 lines
            commands.append(b'\x1d\x56\x41\x10')  # Partial cut
            
            # Send all commands
            for cmd in commands:
                self.socket.send(cmd)
            
            logger.info(f"Receipt printed for transaction {transaction_data.get('id')}")
            return True
            
        except Exception as e:
            logger.error("Error printing receipt: %s", str(e)[:100].replace('\n', ' ').replace('\r', ' '))
            return False
    
    def print_label(self, label_data: dict) -> bool:
        """Print a metal identification label"""
        if not self.connected and not self.connect():
            return False
        
        try:
            commands = []
            
            # Initialize
            commands.append(b'\x1b\x40')
            
            # Label format
            commands.append(b'\x1b\x21\x20')  # Double height
            commands.append(b'\x1b\x61\x01')  # Center
            
            metal_type = label_data.get('metal_type', 'Unknown')
            weight = label_data.get('weight', 0)
            date = datetime.now().strftime('%m/%d/%Y')
            
            commands.append(f"{metal_type}\n".encode())
            commands.append(b'\x1b\x21\x00')  # Normal size
            commands.append(f"Weight: {weight:.2f} lbs\n".encode())
            commands.append(f"Date: {date}\n".encode())
            commands.append(f"ID: {label_data.get('id', 'N/A')}\n".encode())
            
            # Cut
            commands.append(b'\x1b\x64\x02')
            commands.append(b'\x1d\x56\x41\x10')
            
            for cmd in commands:
                self.socket.send(cmd)
            
            return True
            
        except Exception as e:
            logger.error("Error printing label: %s", str(e)[:100].replace('\n', ' ').replace('\r', ' '))
            return False
    
    def get_status(self) -> dict:
        """Get printer status"""
        if not self.connected:
            return {'connected': False, 'status': 'disconnected'}
        
        try:
            # Send status request
            self.socket.send(b'\x1b\x76')
            response = self.socket.recv(1024)
            
            return {
                'connected': True,
                'status': 'ready',
                'paper': 'ok'
            }
        except Exception as e:
            logger.error(f"Error getting printer status: {e}")
            return {'connected': False, 'status': 'error'}