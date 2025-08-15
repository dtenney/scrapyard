# Hardware Setup Guide

## Overview
This guide covers the setup and configuration of hardware devices for the Scrap Yard POS System.

## Supported Hardware

### Weight Scales
**USR-TCP232-410S Serial-to-Ethernet Converter**
- **Purpose**: Connect RS232 scales to network
- **Configuration**: TCP Server mode
- **Default Port**: 8899
- **Supported Scales**: Most RS232 compatible scales

#### Setup Steps:
1. Connect scale to USR-TCP232-410S via RS232
2. Configure device IP address using USR configuration tool
3. Set to TCP Server mode, port 8899
4. Test connection using telnet
5. Add device in admin panel

### Label Printers
**Star Micronics TSP100 Series**
- **Models**: TSP143III, TSP143IIIU, TSP143IIIW
- **Connection**: Ethernet (recommended)
- **Protocol**: ESC/POS commands
- **Paper**: 80mm thermal paper

#### Setup Steps:
1. Connect printer to network
2. Configure static IP address
3. Test printing using Star utility
4. Add printer in admin panel
5. Configure paper size and DPI settings

### Network Cameras
**AXIS M2025-LE Network Camera**
- **Resolution**: Up to 1920x1080
- **Features**: Day/night vision, PoE
- **Protocols**: HTTP, RTSP, MJPEG
- **Authentication**: Basic HTTP auth

#### Setup Steps:
1. Connect camera to PoE switch
2. Configure IP address using AXIS IP Utility
3. Set username/password
4. Test streaming via web browser
5. Add camera in admin panel

### ID Scanners
**Network-enabled Driver's License Scanners**
- **Supported**: Most network-capable ID scanners
- **Protocol**: HTTP POST or TCP socket
- **Data Format**: JSON or XML

## Network Configuration

### IP Address Scheme
- **Scales**: 192.168.1.100-119
- **Printers**: 192.168.1.120-139
- **Cameras**: 192.168.1.140-159
- **Scanners**: 192.168.1.160-179

### Port Configuration
- **Scales**: 8899 (TCP)
- **Printers**: 9100 (TCP)
- **Cameras**: 80 (HTTP)
- **Scanners**: 8080 (HTTP)

### Network Requirements
- **Bandwidth**: 100 Mbps minimum
- **Latency**: <50ms for scales
- **Reliability**: Managed switches recommended
- **Security**: VLAN isolation recommended

## Device Configuration

### Scale Configuration
```json
{
    "ip_address": "192.168.1.100",
    "port": 8899,
    "timeout": 5,
    "precision": 0.01,
    "capacity": 5000,
    "unit": "lbs",
    "tare_command": "T\\r\\n",
    "weight_command": "W\\r\\n"
}
```

### Printer Configuration
```json
{
    "ip_address": "192.168.1.120",
    "port": 9100,
    "model": "TSP143III",
    "paper_width": 80,
    "dpi": 203,
    "cut_type": "partial"
}
```

### Camera Configuration
```json
{
    "ip_address": "192.168.1.140",
    "username": "admin",
    "password": "camera123",
    "resolution": "1920x1080",
    "fps": 15,
    "stream_format": "mjpeg"
}
```

## Troubleshooting

### Scale Issues
- **No weight reading**: Check RS232 connection and baud rate
- **Unstable readings**: Verify scale calibration
- **Connection timeout**: Check network connectivity

### Printer Issues
- **No printing**: Verify IP address and port
- **Garbled output**: Check ESC/POS command format
- **Paper jam**: Clear paper path and reload

### Camera Issues
- **No video**: Check PoE power and network
- **Poor image quality**: Adjust lighting and focus
- **Authentication failed**: Verify username/password

## Maintenance

### Daily Checks
- [ ] Verify all devices online
- [ ] Check scale calibration
- [ ] Test printer paper levels
- [ ] Verify camera image quality

### Weekly Maintenance
- [ ] Clean scale platform
- [ ] Replace printer paper if needed
- [ ] Clean camera lens
- [ ] Check network connections

### Monthly Maintenance
- [ ] Calibrate scales
- [ ] Update device firmware
- [ ] Review device logs
- [ ] Test backup procedures

## Safety Considerations
- Use proper electrical safety procedures
- Ensure adequate ventilation for equipment
- Follow manufacturer safety guidelines
- Implement proper grounding for all devices