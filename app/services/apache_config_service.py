import os
import logging
from typing import List
from app.models.device import Device

logger = logging.getLogger(__name__)

class ApacheConfigService:
    """Service for managing Apache camera proxy configurations"""
    
    APACHE_CONFIG_PATH = '/etc/apache2/sites-available/scrapyard.conf'
    CAMERA_PROXY_MARKER_START = '    # Camera proxies - auto-generated'
    CAMERA_PROXY_MARKER_END = '    # End camera proxies'
    
    @classmethod
    def update_camera_proxies(cls) -> bool:
        """Update Apache config with current camera device proxies"""
        try:
            # Get all active camera devices ordered by ID for consistent numbering
            cameras = Device.query.filter_by(device_type='camera', is_active=True).order_by(Device.id).all()
            
            # Generate proxy configurations
            proxy_configs = []
            for i, camera in enumerate(cameras):
                if camera.ip_address:
                    proxy_configs.append(f'    # Camera {i+1}: {camera.name}')
                    proxy_configs.append(f'    ProxyPass /camera{i+1}/ http://{camera.ip_address}/')
                    proxy_configs.append(f'    ProxyPassReverse /camera{i+1}/ http://{camera.ip_address}/')
                    proxy_configs.append('')
            
            # Read current config using sudo if needed
            import subprocess
            try:
                result = subprocess.run(['sudo', 'cat', cls.APACHE_CONFIG_PATH], 
                                      capture_output=True, text=True, check=True)
                lines = result.stdout.splitlines(keepends=True)
            except subprocess.CalledProcessError:
                logger.error(f"Cannot read Apache config: {cls.APACHE_CONFIG_PATH}")
                return False
            
            # Find and replace camera proxy section
            new_lines = []
            in_camera_section = False
            
            for line in lines:
                if cls.CAMERA_PROXY_MARKER_START in line:
                    in_camera_section = True
                    new_lines.append(line)
                    # Add new proxy configs
                    for config in proxy_configs:
                        new_lines.append(config + '\n')
                elif cls.CAMERA_PROXY_MARKER_END in line:
                    in_camera_section = False
                    new_lines.append(line)
                elif not in_camera_section:
                    new_lines.append(line)
            
            # If markers don't exist, add them before ErrorLog
            if not any(cls.CAMERA_PROXY_MARKER_START in line for line in lines):
                # Find ErrorLog line and insert before it
                for i, line in enumerate(new_lines):
                    if 'ErrorLog' in line:
                        new_lines.insert(i, '    \n')
                        new_lines.insert(i+1, cls.CAMERA_PROXY_MARKER_START + '\n')
                        for config in proxy_configs:
                            new_lines.insert(i+2, config + '\n')
                            i += 1
                        new_lines.insert(i+2, cls.CAMERA_PROXY_MARKER_END + '\n')
                        new_lines.insert(i+3, '    \n')
                        break
            
            # Write updated config using sudo
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                temp_file.writelines(new_lines)
                temp_path = temp_file.name
            
            # Copy temp file to Apache config location with sudo
            result = subprocess.run(['sudo', 'cp', temp_path, cls.APACHE_CONFIG_PATH], 
                                  capture_output=True, text=True)
            os.unlink(temp_path)  # Clean up temp file
            
            if result.returncode == 0:
                logger.info(f"Updated Apache config with {len(cameras)} camera proxies")
                # Log the generated proxy configs for debugging
                for config in proxy_configs:
                    if config.strip():
                        logger.info(f"Added proxy config: {config.strip()}")
                return True
            else:
                logger.error(f"Failed to write Apache config: {result.stderr}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to update Apache camera proxies: {e}")
            return False
    
    @classmethod
    def reload_apache(cls) -> bool:
        """Reload Apache configuration"""
        try:
            import subprocess
            # Try without sudo first, then with sudo if needed
            result = subprocess.run(['systemctl', 'reload', 'apache2'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("Apache configuration reloaded successfully")
                return True
            else:
                # If that fails, try with sudo but don't require password
                result = subprocess.run(['sudo', '-n', 'systemctl', 'reload', 'apache2'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info("Apache configuration reloaded successfully with sudo")
                    return True
                else:
                    logger.warning(f"Apache reload failed, config updated but not reloaded: {result.stderr}")
                    return True  # Config was updated, reload failure is not critical
        except Exception as e:
            logger.error(f"Error reloading Apache: {e}")
            return True  # Don't fail the whole operation if reload fails