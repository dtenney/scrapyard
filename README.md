# Scrap Yard Management System

A comprehensive web-based Point of Sale system for scrap metal yards with hardware integration, compliance tracking, and multi-user support.

## Features

- **Web-based Interface**: Touch-screen friendly Python web application
- **Hardware Integration**: 
  - USR-TCP232-410S serial-to-ethernet weight scales
  - Star Micronics thermal label printers
  - AXIS M2025-LE network cameras
  - CUPS printing support
- **Compliance**: New Jersey regulatory compliance and industry best practices
- **Security**: Role-based access control with user groups
- **Multi-device Support**: Users assigned to specific scales, printers, and cameras

## System Requirements

- Ubuntu Linux
- Apache with mod_wsgi
- PostgreSQL database
- Python 3.8+
- Network connectivity for hardware devices

## Quick Start

1. Run setup script: `sudo ./setup.sh`
2. Configure hardware devices in admin panel
3. Create user accounts and assign device groups
4. Access application at `http://localhost/scrapyard`

## Documentation

- [Requirements](docs/REQUIREMENTS.md)
- [Task List](docs/TASKS.md)
- [Implementation Plan](docs/IMPLEMENTATION.md)
- [Hardware Setup](docs/HARDWARE.md)
- [Compliance Guide](docs/COMPLIANCE.md)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.