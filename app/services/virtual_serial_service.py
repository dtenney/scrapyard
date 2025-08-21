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
            
            # Check if socat is available
            try:
                result = subprocess.run(['which', 'socat'], check=True, capture_output=True, text=True)
                logger.info(f"socat found at: {result.stdout.strip()}")
            except subprocess.CalledProcessError:
                logger.error("socat is not installed. Install with: sudo apt-get install socat")
                return False
            
            # Create socat command
            socat_cmd = [
                'socat', 
                f'pty,link={device_path},raw,echo=0,waitslave',
                f'tcp:{ip_address}:{port}'
            ]
            
            logger.info(f"Creating virtual serial device: {' '.join(socat_cmd)}")
            
            # Try to create device with nohup for persistence
            nohup_cmd = ['nohup'] + socat_cmd
            
            # Start socat process in background
            with open('/dev/null', 'w') as devnull:
                process = subprocess.Popen(
                    nohup_cmd,
                    stdout=devnull,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid,
                    cwd='/tmp'
                )
            
            # Wait for device to be created
            for i in range(30):  # Wait up to 15 seconds
                if os.path.exists(device_path):
                    break
                time.sleep(0.5)
                logger.debug(f"Waiting for device creation... attempt {i+1}")
            
            if os.path.exists(device_path):
                # Set permissions
                try:
                    os.chmod(device_path, 0o666)
                    logger.info(f"Virtual serial device created successfully: {device_path}")
                    return True
                except OSError as e:
                    logger.warning(f"Could not set permissions on {device_path}: {e}")
                    return True  # Device exists, permission error is not critical
            else:
                # Check if socat process failed
                try:
                    _, stderr = process.communicate(timeout=2)
                    logger.error(f"Failed to create virtual serial device: {device_path}")
                    if stderr:
                        logger.error(f"Socat stderr: {stderr.decode()}")
                except subprocess.TimeoutExpired:
                    logger.error(f"Socat process timeout for device: {device_path}")
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
    def test_socat_creation(device_path: str, ip_address: str) -> dict:
        """Test socat device creation with detailed output"""
        try:
            # Check socat availability
            result = subprocess.run(['which', 'socat'], capture_output=True, text=True)
            if result.returncode != 0:
                return {'success': False, 'error': 'socat not found', 'install_cmd': 'sudo apt-get install socat'}
            
            # Test socat command
            test_cmd = [
                'socat', 
                f'pty,link={device_path},raw,echo=0,waitslave',
                f'tcp:{ip_address}:23'
            ]
            
            logger.info(f"Testing socat command: {' '.join(test_cmd)}")
            
            # Run command and capture output
            process = subprocess.Popen(
                test_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait briefly and check if device was created
            time.sleep(2)
            
            if os.path.exists(device_path):
                process.terminate()
                return {'success': True, 'message': f'Device {device_path} created successfully'}
            else:
                stdout, stderr = process.communicate(timeout=5)
                return {
                    'success': False, 
                    'error': 'Device not created',
                    'stdout': stdout,
                    'stderr': stderr,
                    'command': ' '.join(test_cmd)
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
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