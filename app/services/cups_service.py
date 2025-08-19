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
            result = subprocess.run(['/usr/bin/lpstat', '-p'], 
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
            logger.error("Error getting CUPS printers: %s", str(e)[:100].replace('\n', ' ').replace('\r', ' '))
            return []
    
    def print_file(self, printer_name: str, file_path: str, 
                   options: Optional[Dict] = None) -> bool:
        """Print a file using CUPS lp command"""
        import re
        import os
        import shlex
        
        # Validate printer name (alphanumeric, dash, underscore only)
        if not re.match(r'^[a-zA-Z0-9_-]+$', printer_name):
            logger.error("Invalid printer name")
            return False
        
        # Validate file path exists and is safe
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            logger.error("Invalid file path")
            return False
        
        # Validate file path is within allowed directories
        allowed_dirs = ['/var/www/scrapyard/static', '/tmp']
        abs_path = os.path.abspath(file_path)
        if not any(abs_path.startswith(d) for d in allowed_dirs):
            logger.error("File path not in allowed directory")
            return False
        
        # Additional path traversal protection
        if '..' in file_path or file_path.startswith('/'):
            if not abs_path.startswith(tuple(allowed_dirs)):
                logger.error("Path traversal attempt detected")
                return False
        
        try:
            # Use full path to prevent command injection
            cmd = ['/usr/bin/lp', '-d', printer_name, abs_path]
            
            if options:
                # Whitelist allowed options to prevent injection
                allowed_options = {'copies', 'media', 'orientation', 'sides'}
                for key, value in options.items():
                    if key in allowed_options and re.match(r'^[a-zA-Z0-9_.-]+$', str(value)):
                        cmd.extend(['-o', f'{key}={value}'])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=False)
            
            if result.returncode == 0:
                logger.info("File printed successfully")
                return True
            else:
                logger.error("Print job failed")
                return False
                
        except Exception as e:
            logger.error("Error printing file")
            return False
    
    def print_text(self, printer_name: str, text: str, 
                   title: str = "Scrap Receipt") -> bool:
        """Print text content directly"""
        import re
        
        # Validate printer name
        if not re.match(r'^[a-zA-Z0-9_-]+$', printer_name):
            logger.error("Invalid printer name")
            return False
        
        # Validate title (no shell metacharacters)
        if not re.match(r'^[a-zA-Z0-9 _.-]+$', title):
            logger.error("Invalid title format")
            return False
        
        # Limit text length to prevent abuse
        if len(text) > 10000:
            logger.error("Text too long")
            return False
        
        try:
            cmd = ['/usr/bin/lp', '-d', printer_name, '-t', title, '-']
            
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, shell=False)
            
            stdout, stderr = process.communicate(input=text, timeout=30)
            
            if process.returncode == 0:
                logger.info("Text printed successfully to printer")
                return True
            else:
                logger.error("Print job failed")
                return False
                
        except Exception as e:
            logger.error("Error printing text")
            return False
    
    def get_printer_status(self, printer_name: str) -> Dict:
        """Get status of specific printer"""
        import re
        
        # Validate printer name
        if not re.match(r'^[a-zA-Z0-9_-]+$', printer_name):
            logger.error("Invalid printer name")
            return {'status': 'error', 'message': 'Invalid printer name'}
        
        try:
            result = subprocess.run(['/usr/bin/lpstat', '-p', printer_name], 
                                  capture_output=True, text=True, timeout=10, shell=False)
            
            if result.returncode == 0:
                status_line = result.stdout.strip()
                if 'idle' in status_line:
                    return {'status': 'ready', 'message': 'Printer ready'}
                elif 'printing' in status_line:
                    return {'status': 'busy', 'message': 'Printer busy'}
                else:
                    return {'status': 'unknown', 'message': 'Status unknown'}
            else:
                return {'status': 'error', 'message': 'Printer not found'}
                
        except Exception as e:
            logger.error("Error getting printer status")
            return {'status': 'error', 'message': 'Status check failed'}