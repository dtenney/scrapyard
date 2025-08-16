#!/bin/bash

# Scrap Yard Management System Setup Script
# Ubuntu Linux Installation

set -e

echo "=== Scrap Yard Management System Setup ==="

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get install -y \
    apache2 \
    postgresql \
    postgresql-contrib \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    libpq-dev \
    libapache2-mod-wsgi-py3 \
    cups \
    cups-client \
    libcups2-dev \
    python3-opencv \
    git \
    nginx \
    redis-server \
    supervisor \
    ufw \
    fail2ban

# Configure firewall
echo "Configuring firewall..."
sudo ufw --force enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 631/tcp  # CUPS

# Create application user
echo "Creating application user..."
sudo useradd -m -s /bin/bash scrapyard || true
sudo usermod -aG www-data scrapyard

# Create application directory
echo "Setting up application directory..."
sudo mkdir -p /var/www/scrapyard
sudo chown scrapyard:www-data /var/www/scrapyard
sudo chmod 755 /var/www/scrapyard

# Copy application files
echo "Copying application files..."
sudo cp -r . /var/www/scrapyard/
sudo chown -R scrapyard:www-data /var/www/scrapyard

# Create Python virtual environment
echo "Creating Python virtual environment..."
cd /var/www/scrapyard
sudo -u scrapyard python3 -m venv venv
sudo -u scrapyard ./venv/bin/pip install --upgrade pip
sudo -u scrapyard ./venv/bin/pip install -r requirements.txt

# Configure PostgreSQL
echo "Configuring PostgreSQL..."
# Reset database completely
sudo chmod +x /var/www/scrapyard/reset_database.sh
sudo /var/www/scrapyard/reset_database.sh

# Configure Apache
echo "Configuring Apache..."
sudo cp config/apache-scrapyard.conf /etc/apache2/sites-available/scrapyard.conf
sudo a2ensite scrapyard
sudo a2dissite 000-default
sudo a2enmod wsgi
sudo a2enmod ssl
sudo a2enmod rewrite
sudo a2enmod headers

# Create SSL certificate (self-signed for development)
echo "Creating SSL certificate..."
sudo mkdir -p /etc/ssl/scrapyard
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/scrapyard/scrapyard.key \
    -out /etc/ssl/scrapyard/scrapyard.crt \
    -subj "/C=US/ST=NJ/L=Newark/O=ScrapYard/CN=localhost"

# Configure CUPS
echo "Configuring CUPS..."
sudo systemctl enable cups
sudo systemctl start cups
sudo usermod -aG lpadmin scrapyard

# Configure Redis
echo "Configuring Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Configure Supervisor
echo "Configuring Supervisor..."
sudo cp config/supervisor-scrapyard.conf /etc/supervisor/conf.d/scrapyard.conf
sudo systemctl enable supervisor
sudo systemctl start supervisor

# Initialize database
echo "Initializing database..."
cd /var/www/scrapyard

# Initialize database tables
sudo -u scrapyard ./venv/bin/python -c "
from app import create_app, db
from app.models.user import User, UserGroup, UserGroupMember
from app.models.device import Device
from app.models.material import Material
from app.models.customer import Customer
from app.models.permissions import Permission, GroupPermission
from app.services.setup_service import initialize_default_groups
from app.routes.admin import load_materials_csv
app = create_app()
with app.app_context():
    db.create_all()
    initialize_default_groups()
    
    # Load materials from CSV automatically
    print('Loading materials from CSV...')
    try:
        result = load_materials_csv()
        print('Materials loaded successfully')
    except Exception as e:
        print(f'Materials loading failed: {e}')
    
    print('Database initialized successfully')
"

# Set permissions
echo "Setting final permissions..."
sudo chown -R scrapyard:www-data /var/www/scrapyard
sudo chmod -R 755 /var/www/scrapyard
sudo chmod -R 644 /var/www/scrapyard/app/static
sudo chmod +x /var/www/scrapyard/app.py

# Start Celery services
echo "Starting Celery services..."
sudo chmod +x /var/www/scrapyard/scripts/start_celery.sh
sudo -u scrapyard /var/www/scrapyard/scripts/start_celery.sh

# Restart services
echo "Restarting services..."
sudo systemctl restart apache2
sudo systemctl restart postgresql
sudo systemctl restart redis-server
sudo supervisorctl reread
sudo supervisorctl update

echo "=== Setup Complete ==="
echo "Application URL: https://localhost/scrapyard"
echo "Default admin user will be created on first access"
echo "Check logs: sudo tail -f /var/log/apache2/error.log"