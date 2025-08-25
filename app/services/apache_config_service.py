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
            # Get all active camera devices
            cameras = Device.query.filter_by(device_type='camera', is_active=True).all()
            
            # Generate proxy configurations
            proxy_configs = []
            for i, camera in enumerate(cameras):
                if camera.ip_address:
                    proxy_configs.append(f'    # Camera {i+1}: {camera.name}')
                    proxy_configs.append(f'    ProxyPass /camera{i+1}/ http://{camera.ip_address}/')
                    proxy_configs.append(f'    ProxyPassReverse /camera{i+1}/ http://{camera.ip_address}/')
                    proxy_configs.append('')
            
            # Read current config
            if not os.path.exists(cls.APACHE_CONFIG_PATH):
                logger.error(f"Apache config not found: {cls.APACHE_CONFIG_PATH}")
                return False
                
            with open(cls.APACHE_CONFIG_PATH, 'r') as f:
                lines = f.readlines()
            
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
            
            # Write updated config
            with open(cls.APACHE_CONFIG_PATH, 'w') as f:
                f.writelines(new_lines)
            
            logger.info(f"Updated Apache config with {len(cameras)} camera proxies")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update Apache camera proxies: {e}")
            return False
    
    @classmethod
    def reload_apache(cls) -> bool:
        """Reload Apache configuration"""
        try:
            import subprocess
            result = subprocess.run(['sudo', 'systemctl', 'reload', 'apache2'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("Apache configuration reloaded successfully")
                return True
            else:
                logger.error(f"Failed to reload Apache: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error reloading Apache: {e}")
            return False