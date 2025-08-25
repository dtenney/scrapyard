#!/bin/bash

# Scrap Yard Management System Setup Script
# Ubuntu Linux Installation

set -e

echo "=== Scrap Yard Management System Setup ==="

# Clean up existing processes
echo "Cleaning up existing processes..."
# Supervisor removed - no longer needed

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
    tesseract-ocr \
    git \
    socat \
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
sudo useradd -m -s /bin/bash -g www-data scrapyard || true

# Configure sudo permissions for scrapyard user
echo "Configuring sudo permissions..."
cat > /tmp/scrapyard-sudo << 'EOF'
# Allow scrapyard user to manage Apache configuration without password
scrapyard ALL=(ALL) NOPASSWD: /bin/cat /etc/apache2/sites-available/scrapyard.conf
scrapyard ALL=(ALL) NOPASSWD: /bin/cp * /etc/apache2/sites-available/scrapyard.conf
scrapyard ALL=(ALL) NOPASSWD: /bin/systemctl reload apache2
scrapyard ALL=(ALL) NOPASSWD: /bin/systemctl restart apache2
EOF
sudo mv /tmp/scrapyard-sudo /etc/sudoers.d/scrapyard
sudo chown root:root /etc/sudoers.d/scrapyard
sudo chmod 440 /etc/sudoers.d/scrapyard

# Create application directory
echo "Setting up application directory..."
sudo mkdir -p /var/www/scrapyard
sudo chown scrapyard:www-data /var/www/scrapyard
sudo chmod 755 /var/www/scrapyard

# Copy application files
echo "Copying application files..."
sudo cp -r . /var/www/scrapyard/
sudo chown -R scrapyard:www-data /var/www/scrapyard

# Generate Flask secret key and database password
echo "Generating Flask secret key and database password..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
DB_PASSWORD=${SCRAPYARD_DB_PASSWORD:-$(openssl rand -base64 32)}

# Export password for database setup
export SCRAPYARD_DB_PASSWORD=$DB_PASSWORD

# Create .env file with secure configuration
cat > /tmp/scrapyard.env << EOF
SECRET_KEY=$SECRET_KEY
FLASK_ENV=production
DATABASE_URL=postgresql://scrapyard:$DB_PASSWORD@localhost/scrapyard_db
SCRAPYARD_DB_PASSWORD=$DB_PASSWORD
# API Keys - Replace with actual values
GEOAPIFY_API_KEY=your_geoapify_api_key_here
EOF

sudo mv /tmp/scrapyard.env /var/www/scrapyard/.env
sudo chown scrapyard:www-data /var/www/scrapyard/.env
sudo chmod 600 /var/www/scrapyard/.env

# Create Python virtual environment
echo "Creating Python virtual environment..."
cd /var/www/scrapyard
sudo -u scrapyard python3 -m venv venv
sudo -u scrapyard ./venv/bin/pip install --upgrade pip
if [ -f requirements.txt ]; then
    sudo -u scrapyard ./venv/bin/pip install -r requirements.txt
else
    echo "Error: requirements.txt not found"
    exit 1
fi

# Configure PostgreSQL
echo "Configuring PostgreSQL..."
# Start PostgreSQL service
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Drop existing database and user if they exist
echo "Cleaning up existing database..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS scrapyard_db;" || true
sudo -u postgres psql -c "DROP USER IF EXISTS scrapyard;" || true

# Create database user and database
echo "Creating database user and database..."
sudo -u postgres createuser scrapyard
sudo -u postgres createdb scrapyard_db -O scrapyard
sudo -u postgres psql -c "ALTER USER scrapyard PASSWORD '$DB_PASSWORD';"

# Configure PostgreSQL for local connections
echo "Configuring PostgreSQL authentication..."
PG_CONFIG_DIR=$(sudo -u postgres psql -t -c "SHOW config_file;" | xargs dirname)
if [ ! -d "$PG_CONFIG_DIR" ]; then
    # Fallback: find the actual config directory
    PG_CONFIG_DIR=$(find /etc/postgresql -name "pg_hba.conf" -exec dirname {} \; | head -1)
fi

# Backup original pg_hba.conf
sudo cp $PG_CONFIG_DIR/pg_hba.conf $PG_CONFIG_DIR/pg_hba.conf.backup

# Update pg_hba.conf for local connections
sudo sed -i 's/local   all             all                                     peer/local   all             all                                     md5/' $PG_CONFIG_DIR/pg_hba.conf
sudo sed -i 's/host    all             all             127.0.0.1\/32            ident/host    all             all             127.0.0.1\/32            md5/' $PG_CONFIG_DIR/pg_hba.conf

# Restart PostgreSQL to apply changes
sudo systemctl restart postgresql

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

# Redis removed - no longer needed

# Supervisor removed - no longer needed

# Initialize database
echo "Initializing database..."
cd /var/www/scrapyard

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if sudo -u scrapyard PGPASSWORD=$DB_PASSWORD psql -h localhost -U scrapyard -d scrapyard_db -c "SELECT 1;" >/dev/null 2>&1; then
        echo "PostgreSQL is ready"
        break
    fi
    echo "Waiting for PostgreSQL... ($i/30)"
    sleep 2
done

# Create database initialization script
cat > /tmp/init_db.py << 'DBEOF'
import os
import sys
sys.path.insert(0, '/var/www/scrapyard')

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv('/var/www/scrapyard/.env')

try:
    from app import create_app, db
    from app.models.user import User, UserGroup, UserGroupMember
    from app.models.device import Device
    from app.models.material import Material
    from app.models.customer import Customer
    from app.models.permissions import Permission, GroupPermission
    from app.services.setup_service import initialize_default_groups
    
    app = create_app()
    with app.app_context():
        print('Creating database tables...')
        db.create_all()
        
        print('Initializing default groups...')
        initialize_default_groups()
        
        print('Loading materials from CSV...')
        import csv
        
        # Load materials from CSV file
        with open('/var/www/scrapyard/data/materials.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            count = 0
            
            for row in reader:
                code = row['Code'].strip()
                description = row['Description'].strip()
                our_price = float(row['Our Price']) if row['Our Price'] else 0.0
                category = row['Category'].strip()
                material_type = row['Type'].strip()
                
                is_ferrous = material_type == 'Ferrous'
                
                # Check if material already exists
                existing = Material.query.filter_by(code=code).first()
                if not existing:
                    material = Material(
                        code=code,
                        description=description,
                        category=category,
                        is_ferrous=is_ferrous,
                        price_per_pound=our_price
                    )
                    db.session.add(material)
                    count += 1
            
            db.session.commit()
            print(f'Materials loaded successfully: {count} items')
        print('Database initialized successfully')
        
except Exception as e:
    print(f'Database initialization failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
DBEOF

# Run database initialization with environment variables
sudo -u scrapyard SCRAPYARD_DB_PASSWORD=$DB_PASSWORD ./venv/bin/python /tmp/init_db.py

# Clean up temporary file
rm -f /tmp/init_db.py

# Create upload directories with proper permissions
echo "Creating upload directories..."
sudo mkdir -p /var/www/scrapyard/uploads/customer_photos
sudo mkdir -p /var/www/scrapyard/uploads/logos
sudo chown -R scrapyard:www-data /var/www/scrapyard/uploads
sudo chmod -R 775 /var/www/scrapyard/uploads

# Set permissions
echo "Setting final permissions..."
sudo chown -R scrapyard:www-data /var/www/scrapyard
sudo chmod -R 755 /var/www/scrapyard
sudo chmod -R 644 /var/www/scrapyard/app/static
sudo chmod +x /var/www/scrapyard/app.py

# Restore 775 permissions for upload directories
sudo chmod -R 775 /var/www/scrapyard/uploads

# Celery services removed - no longer needed

# Restart services
echo "Restarting services..."
sudo systemctl restart apache2
sudo systemctl restart postgresql

echo "=== Setup Complete ==="
echo "Application URL: https://localhost/scrapyard"
echo "Default admin user will be created on first access"
echo "Check logs: sudo tail -f /var/log/apache2/error.log"
echo ""
echo "IMPORTANT: Configure API keys in /var/www/scrapyard/.env file:"
echo "  - GEOAPIFY_API_KEY for address validation"