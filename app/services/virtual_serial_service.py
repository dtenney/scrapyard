import subprocess
import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class VirtualSerialService:
    """Service for managing virtual serial devices with socat"""
    
    @staticmethod
    def create_virtual_serial(device_path: str, ip_address: str, port: int = 23) -> bool:
        """Create a virtual serial device using socat"""
        try:
            # Kill any existing socat process for this device
            VirtualSerialService.destroy_virtual_serial(device_path)
            
            # Ensure directory exists
            device_dir = os.path.dirname(device_path)
            if device_dir and not os.path.exists(device_dir):
                os.makedirs(device_dir, mode=0o755, exist_ok=True)
            
            # Create socat command
            socat_cmd = [
                'socat', 
                f'pty,link={device_path},raw,echo=0,waitslave',
                f'tcp:{ip_address}:{port}'
            ]
            
            logger.info(f"Creating virtual serial device: {' '.join(socat_cmd)}")
            
            # Start socat process in background
            process = subprocess.Popen(
                socat_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )
            
            # Wait for device to be created
            for i in range(20):  # Wait up to 10 seconds
                if os.path.exists(device_path):
                    break
                time.sleep(0.5)
                logger.debug(f"Waiting for device creation... attempt {i+1}")
            
            if os.path.exists(device_path):
                # Set permissions
                os.chmod(device_path, 0o666)
                logger.info(f"Virtual serial device created successfully: {device_path}")
                return True
            else:
                # Check if socat process failed
                stdout, stderr = process.communicate(timeout=1)
                logger.error(f"Failed to create virtual serial device: {device_path}")
                logger.error(f"Socat stdout: {stdout.decode() if stdout else 'None'}")
                logger.error(f"Socat stderr: {stderr.decode() if stderr else 'None'}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating virtual serial device: {str(e)[:100]}")
            return False
    
    @staticmethod
    def destroy_virtual_serial(device_path: str) -> bool:
        """Destroy a virtual serial device by killing socat process"""
        try:
            # Find and kill socat processes using this device
            result = subprocess.run(
                ['pgrep', '-f', f'socat.*{device_path}'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        subprocess.run(['kill', pid], check=False)
                        
            # Remove device file if it exists
            if os.path.exists(device_path):
                os.unlink(device_path)
                
            logger.info(f"Virtual serial device destroyed: {device_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error destroying virtual serial device: {str(e)[:100]}")
            return False
    
    @staticmethod
    def is_device_active(device_path: str) -> bool:
        """Check if virtual serial device is active"""
        try:
            if not os.path.exists(device_path):
                return False
                
            # Check if socat process is running for this device
            result = subprocess.run(
                ['pgrep', '-f', f'socat.*{device_path}'],
                capture_output=True
            )
            
            return result.returncode == 0
            
        except Exception:
            return False