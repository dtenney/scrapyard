import subprocess
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class CUPSService:
    """CUPS printing service using command line tools"""
    
    def __init__(self):
        self.available_printers = []
        self.refresh_printers()
    
    def refresh_printers(self) -> List[Dict]:
        """Get list of available CUPS printers"""
        try:
            result = subprocess.run(['lpstat', '-p'], 
                                  capture_output=True, text=True, timeout=10)
            
            printers = []
            for line in result.stdout.split('\n'):
                if line.startswith('printer'):
                    parts = line.split()
                    if len(parts) >= 2:
                        printer_name = parts[1]
                        status = 'idle' if 'idle' in line else 'busy'
                        printers.append({
                            'name': printer_name,
                            'status': status,
                            'description': ' '.join(parts[2:]) if len(parts) > 2 else ''
                        })
            
            self.available_printers = printers
            return printers
            
        except Exception as e:
            logger.error(f"Error getting CUPS printers: {e}")
            return []
    
    def print_file(self, printer_name: str, file_path: str, 
                   options: Optional[Dict] = None) -> bool:
        """Print a file using CUPS lp command"""
        try:
            cmd = ['lp', '-d', printer_name, file_path]
            
            if options:
                for key, value in options.items():
                    cmd.extend(['-o', f'{key}={value}'])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"File printed successfully to {printer_name}")
                return True
            else:
                logger.error(f"Print failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error printing file: {e}")
            return False
    
    def print_text(self, printer_name: str, text: str, 
                   title: str = "Scrap Receipt") -> bool:
        """Print text content directly"""
        try:
            cmd = ['lp', '-d', printer_name, '-t', title, '-']
            
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True)
            
            stdout, stderr = process.communicate(input=text, timeout=30)
            
            if process.returncode == 0:
                logger.info(f"Text printed successfully to {printer_name}")
                return True
            else:
                logger.error(f"Print failed: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error printing text: {e}")
            return False
    
    def get_printer_status(self, printer_name: str) -> Dict:
        """Get status of specific printer"""
        try:
            result = subprocess.run(['lpstat', '-p', printer_name], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                status_line = result.stdout.strip()
                if 'idle' in status_line:
                    return {'status': 'ready', 'message': 'Printer ready'}
                elif 'printing' in status_line:
                    return {'status': 'busy', 'message': 'Printer busy'}
                else:
                    return {'status': 'unknown', 'message': status_line}
            else:
                return {'status': 'error', 'message': 'Printer not found'}
                
        except Exception as e:
            logger.error(f"Error getting printer status: {e}")
            return {'status': 'error', 'message': str(e)}