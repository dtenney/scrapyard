#!/usr/bin/env python3
"""
Manual script to create virtual serial device for testing
Usage: python3 create_virtual_serial.py /dev/ttyV0 192.168.1.100
"""

import sys
import subprocess
import os
import time

def create_virtual_serial(device_path, ip_address, port=23):
    """Create virtual serial device using socat"""
    
    # Check if socat is available
    try:
        subprocess.run(['which', 'socat'], check=True, capture_output=True)
        print("✓ socat is available")
    except subprocess.CalledProcessError:
        print("✗ socat not found. Install with: sudo apt-get install socat")
        return False
    
    # Kill existing processes
    try:
        result = subprocess.run(['pgrep', '-f', f'socat.*{device_path}'], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    subprocess.run(['kill', pid], check=False)
                    print(f"✓ Killed existing socat process: {pid}")
    except Exception:
        pass
    
    # Remove existing device
    if os.path.exists(device_path):
        os.unlink(device_path)
        print(f"✓ Removed existing device: {device_path}")
    
    # Create directory if needed
    device_dir = os.path.dirname(device_path)
    if device_dir and not os.path.exists(device_dir):
        os.makedirs(device_dir, mode=0o755, exist_ok=True)
        print(f"✓ Created directory: {device_dir}")
    
    # Create socat command
    socat_cmd = [
        'socat', 
        f'pty,link={device_path},raw,echo=0,waitslave',
        f'tcp:{ip_address}:{port}'
    ]
    
    print(f"Creating virtual serial device: {' '.join(socat_cmd)}")
    
    # Start socat process
    try:
        process = subprocess.Popen(
            socat_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # Wait for device creation
        for i in range(10):
            if os.path.exists(device_path):
                break
            time.sleep(0.5)
            print(f"Waiting... {i+1}/10")
        
        if os.path.exists(device_path):
            os.chmod(device_path, 0o666)
            print(f"✓ Virtual serial device created: {device_path}")
            print(f"✓ Process ID: {process.pid}")
            return True
        else:
            _, stderr = process.communicate(timeout=2)
            print(f"✗ Failed to create device")
            if stderr:
                print(f"Error: {stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 create_virtual_serial.py <device_path> <ip_address>")
        print("Example: python3 create_virtual_serial.py /tmp/ttyV0 192.168.1.100")
        sys.exit(1)
    
    device_path = sys.argv[1]
    ip_address = sys.argv[2]
    
    print(f"Creating virtual serial device: {device_path} -> {ip_address}:23")
    success = create_virtual_serial(device_path, ip_address)
    sys.exit(0 if success else 1)