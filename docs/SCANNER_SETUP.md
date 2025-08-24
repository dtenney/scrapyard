# Gemalto CR5400 License Scanner Setup

## Overview
The scrapyard application supports the Gemalto CR5400 driver's license scanner using the WebSerial API for direct browser communication.

## Requirements

### Browser Support
- **Chrome 89+** or **Edge 89+** (WebSerial API support)
- **HTTPS connection** (required for WebSerial API)
- **User permission** (browser will prompt for device access)

### Hardware Setup
1. Connect Gemalto CR5400 to USB port
2. Install device drivers if required by OS
3. Verify device appears in Device Manager (Windows) or lsusb (Linux)

## Usage

### Scanning Process
1. Navigate to Customer Lookup page
2. Click "Add New Customer" 
3. Click "Scan Driver's License" button
4. Browser will prompt for device permission - select CR5400
5. Insert driver's license into scanner
6. Form fields will auto-populate with extracted data

### Troubleshooting

**Scanner not detected:**
- Ensure browser supports WebSerial API
- Check USB connection
- Verify device drivers installed
- Try different USB port

**Permission denied:**
- Refresh page and try again
- Check browser security settings
- Ensure HTTPS connection

**Scan timeout:**
- Check license is properly inserted
- Verify scanner power/connection
- Try scanning again

## Technical Details

### WebSerial Configuration
- **Baud Rate:** 9600
- **Data Bits:** 8
- **Stop Bits:** 1
- **Parity:** None
- **Flow Control:** None

### Vendor/Product IDs
- **Vendor ID:** 0x08e6 (Gemalto)
- **Product ID:** 0x5400 (CR5400)

### Data Format
Scanner returns parsed license data:
- Name
- License Number  
- Date of Birth
- Address

## Security Notes
- WebSerial requires explicit user permission
- Scanner communication is local only
- No license data transmitted to external servers
- HTTPS required for security context