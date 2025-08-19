# Scrapyard Installation Log

## Automated Setup Script

The scrapyard system includes an automated setup script that handles the complete installation process.

### Quick Installation
```bash
# Clone repository
git clone https://github.com/dtenney/scrapyard.git
cd scrapyard

# Run setup script
sudo ./setup.sh
```

## Setup Script Actions

The `setup.sh` script performs the following operations:

### 1. System Package Installation
- Updates system packages
- Installs Apache2 with mod_wsgi
- Installs PostgreSQL database server
- Installs Python 3 and development tools
- Installs Redis server for Celery
- Installs CUPS for printer support
- Installs security tools (ufw, fail2ban)

### 2. Security Configuration
- Enables UFW firewall
- Opens required ports (22, 80, 443, 631)
- Creates application user with proper permissions

### 3. Application Setup
- Creates `/var/www/scrapyard` directory
- Copies application files with correct ownership
- Creates Python virtual environment
- Installs Python dependencies from requirements.txt

### 4. Database Configuration
- Runs `reset_database.sh` to create PostgreSQL user and database
- Initializes database tables using SQLAlchemy models
- Creates default user groups and permissions
- Loads material catalog from CSV data

### 5. Web Server Configuration
- Configures Apache virtual host from `config/apache-scrapyard.conf`
- Enables required Apache modules (wsgi, ssl, rewrite, headers)
- Creates self-signed SSL certificate for HTTPS
- Disables default Apache site

### 6. Service Configuration
- Configures CUPS printing service
- Sets up Redis server for background tasks
- Configures Supervisor for Celery worker management
- Starts all required system services

### 7. Background Task Setup
- Configures Celery worker and beat scheduler
- Sets up price scraping and automated tasks
- Starts background services via Supervisor

### 8. Final System Configuration
- Sets proper file permissions and ownership
- Restarts all services
- Validates installation

## Post-Installation Steps

### 1. Access Application
```bash
# Application will be available at:
https://localhost/scrapyard
```

### 2. Initial Admin Setup
- First visit will redirect to setup page
- Create admin account with email and password
- Login with admin credentials

### 3. Hardware Configuration
- Navigate to Admin → Devices
- Add scales: USR-TCP232-410S devices with IP addresses
- Add printers: Star Micronics thermal printers
- Add cameras: AXIS M2025-LE network cameras
- Test device connections

### 4. User Management
- Admin → Users to create cashier accounts
- Assign users to device groups (scales, printers, cameras)
- Configure role-based permissions

### 5. Material Management
- Materials are pre-loaded from CSV during setup
- Admin → Materials to view/edit material catalog
- Use "Update Market Prices" for current pricing
- Configure SGT price scraping for automated updates

### 6. Customer Management
- Cashier interface includes customer lookup
- Add customers with driver's license scanning
- Address validation via Smarty Streets (requires API keys)

## Installation Verification

### Check Service Status
```bash
# Verify all services are running
sudo systemctl status apache2
sudo systemctl status postgresql
sudo systemctl status redis-server
sudo supervisorctl status

# Check application logs
sudo tail -f /var/log/apache2/error.log
sudo tail -f /var/log/supervisor/scrapyard-celery.log
```

### Test Database Connection
```bash
# Connect to database
psql -U scrapyard -d scrapyard -h localhost

# List tables
\dt

# Check materials loaded
SELECT COUNT(*) FROM materials;
```

### Verify Web Access
```bash
# Test HTTP redirect
curl -I http://localhost/scrapyard

# Test HTTPS access
curl -k -I https://localhost/scrapyard
```

## Troubleshooting Setup Issues

### Setup Script Fails
```bash
# Re-run with verbose output
bash -x setup.sh

# Check specific service logs
journalctl -u apache2 -f
journalctl -u postgresql -f
```

### Database Issues
```bash
# Reset database completely
sudo ./reset_database.sh

# Manually initialize
sudo -u scrapyard /var/www/scrapyard/venv/bin/python -c "
from app import create_app, db
app = create_app()
with app.app_context(): db.create_all()
"
```

### Permission Issues
```bash
# Fix all permissions
sudo chown -R scrapyard:www-data /var/www/scrapyard
sudo chmod -R 755 /var/www/scrapyard
sudo systemctl restart apache2
```

### Log File Locations
- Setup log: Console output during `./setup.sh`
- Apache errors: `/var/log/apache2/error.log`
- Application errors: `/var/log/apache2/scrapyard_error.log`
- Celery logs: `/var/log/supervisor/scrapyard-celery*.log`
- PostgreSQL: `/var/log/postgresql/postgresql-*.log`

## Configuration Files

The setup script uses these configuration files:

- `setup.sh` - Main installation script
- `reset_database.sh` - Database initialization
- `config/apache-scrapyard.conf` - Apache virtual host
- `config/supervisor-scrapyard.conf` - Celery process management
- `scripts/start_celery.sh` - Celery startup script
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variables template

## Security Features

### Automatic Security Setup
- UFW firewall enabled with minimal required ports
- Self-signed SSL certificate for HTTPS
- Fail2ban for intrusion prevention
- Separate application user with limited privileges
- CSRF protection on all forms

### Post-Setup Security
- Change admin password immediately
- Configure production SSL certificate
- Set up regular security updates
- Monitor access logs
- Configure backup strategy

## System Requirements Met

- ✅ Ubuntu Linux (18.04+)
- ✅ Apache 2.4+ with mod_wsgi
- ✅ PostgreSQL 12+ database
- ✅ Python 3.8+ with virtual environment
- ✅ Redis for background tasks
- ✅ CUPS for printer support
- ✅ SSL/HTTPS encryption
- ✅ Process supervision (Supervisor)
- ✅ Firewall configuration (UFW)

## Installation Complete

After successful setup:
1. Access https://localhost/scrapyard
2. Complete admin account creation
3. Configure hardware devices
4. Begin scrap metal operations

**Setup script handles all technical installation automatically.**

Installation Method: Automated via setup.sh script
Last Updated: 2025-01-19