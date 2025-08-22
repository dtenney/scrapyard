import logging
import os
from app.models.device import Device
from app.services.virtual_serial_service import VirtualSerialService

logger = logging.getLogger(__name__)

def initialize_virtual_serial_devices():
    """Initialize all virtual serial devices for scales on startup"""
    try:
        scales = Device.query.filter_by(device_type='scale').all()
        
        for scale in scales:
            if scale.serial_port and scale.ip_address:
                # Check if device exists and process is running
                if not os.path.exists(scale.serial_port) or not VirtualSerialService.is_device_active(scale.serial_port):
                    logger.info(f"Recreating virtual serial device: {scale.serial_port}")
                    success = VirtualSerialService.create_virtual_serial(scale.serial_port, scale.ip_address)
                    if success:
                        logger.info(f"Virtual serial device restored: {scale.serial_port}")
                    else:
                        logger.error(f"Failed to restore virtual serial device: {scale.serial_port}")
                else:
                    logger.info(f"Virtual serial device already active: {scale.serial_port}")
                    
    except Exception as e:
        logger.error(f"Error initializing virtual serial devices: {str(e)[:100]}")