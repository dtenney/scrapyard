# Scrapyard Installation Log

## System Requirements
- Ubuntu Linux
- Apache with mod_wsgi
- PostgreSQL database
- Python 3.8+
- Network connectivity for hardware devices

## Installation Steps

### 1. System Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y apache2 postgresql postgresql-contrib python3 python3-pip python3-venv libpq-dev python3-dev apache2-dev redis-server

# Enable Apache modules
sudo a2enmod wsgi
sudo a2enmod ssl
sudo a2enmod rewrite
```

### 2. Database Setup
```bash
# Switch to postgres user and create database
sudo -u postgres createuser -P scrapyard
sudo -u postgres createdb -O scrapyard scrapyard

# Test database connection
psql -U scrapyard -d scrapyard -h localhost -c "SELECT version();"
```

### 3. Application Setup
```bash
# Clone repository
cd /var/www
sudo git clone https://github.com/dtenney/scrapyard.git
sudo chown -R www-data:www-data scrapyard
cd scrapyard

# Create virtual environment
sudo -u www-data python3 -m venv venv
sudo -u www-data ./venv/bin/pip install -r requirements.txt

# Set up environment variables
sudo -u www-data cp .env.example .env
# Edit .env with actual values:
# DATABASE_URL=postgresql://scrapyard:password@localhost/scrapyard
# SECRET_KEY=your_secret_key_here
# SMARTY_AUTH_ID=your_smarty_auth_id
# SMARTY_AUTH_TOKEN=your_smarty_auth_token
```

### 4. Database Migration
```bash
# Run database migrations
sudo -u www-data psql -U scrapyard -d scrapyard -h localhost < fix_database_tables.sql
sudo -u www-data psql -U scrapyard -d scrapyard -h localhost < add_customer_address_fields.sql

# Initialize database with materials
sudo -u www-data ./venv/bin/python3 -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Database initialized')
"
```

### 5. Apache Configuration
```bash
# Copy Apache configuration
sudo cp config/apache-scrapyard.conf /etc/apache2/sites-available/
sudo a2ensite apache-scrapyard
sudo a2dissite 000-default
sudo systemctl reload apache2
```

### 6. Celery Setup
```bash
# Copy supervisor configuration
sudo cp config/supervisor-scrapyard.conf /etc/supervisor/conf.d/
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start scrapyard-celery
sudo supervisorctl start scrapyard-celery-beat
```

### 7. SSL Certificate (Optional)
```bash
# Install Let's Encrypt
sudo apt install -y certbot python3-certbot-apache
sudo certbot --apache -d yourdomain.com
```

### 8. Final Steps
```bash
# Set proper permissions
sudo chown -R www-data:www-data /var/www/scrapyard
sudo chmod -R 755 /var/www/scrapyard

# Restart services
sudo systemctl restart apache2
sudo systemctl restart redis-server
sudo supervisorctl restart all

# Check status
sudo systemctl status apache2
sudo systemctl status postgresql
sudo systemctl status redis-server
sudo supervisorctl status
```

## Post-Installation

### 1. Initial Admin Setup
- Navigate to http://localhost/scrapyard
- Complete admin account setup
- Configure hardware devices in admin panel

### 2. Hardware Configuration
- Add scales, printers, and cameras in Device Management
- Test device connections
- Assign devices to user groups

### 3. Material Setup
- Load materials from CSV: Admin → Materials → Load from CSV
- Update prices: Admin → Materials → Update Market Prices
- Configure SGT price scraping: Admin → Materials → Prepopulate SGT Prices

### 4. User Management
- Create user accounts in Admin → Users
- Assign users to appropriate groups
- Configure device access permissions

## Troubleshooting

### Common Issues

#### Database Connection Error
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Verify database exists
sudo -u postgres psql -l | grep scrapyard

# Test connection
psql -U scrapyard -d scrapyard -h localhost
```

#### Apache Permission Issues
```bash
# Fix ownership
sudo chown -R www-data:www-data /var/www/scrapyard

# Check Apache error log
sudo tail -f /var/log/apache2/error.log
```

#### Celery Not Starting
```bash
# Check supervisor status
sudo supervisorctl status

# Restart Celery services
sudo supervisorctl restart scrapyard-celery
sudo supervisorctl restart scrapyard-celery-beat

# Check logs
sudo tail -f /var/log/supervisor/scrapyard-celery.log
```

#### CSRF Token Errors
- Ensure SECRET_KEY is set in .env
- Clear browser cache and cookies
- Restart Apache after configuration changes

### Log Files
- Apache: `/var/log/apache2/error.log`
- Application: `/media/david/apache_logs/scrapyard_error.log`
- Celery: `/var/log/supervisor/scrapyard-celery.log`
- Database: `/var/log/postgresql/postgresql-*.log`

## Security Checklist
- [ ] Change default admin password
- [ ] Configure firewall (ufw)
- [ ] Set up SSL certificate
- [ ] Configure backup strategy
- [ ] Update system packages regularly
- [ ] Monitor log files for errors

## Backup Strategy
```bash
# Database backup
pg_dump -U scrapyard -h localhost scrapyard > backup_$(date +%Y%m%d).sql

# Application backup
tar -czf scrapyard_backup_$(date +%Y%m%d).tar.gz /var/www/scrapyard
```

## Version Information
- Application Version: Latest from GitHub
- Python: 3.8+
- PostgreSQL: 12+
- Apache: 2.4+
- Redis: 6.0+

Last Updated: $(date)