#!/bin/bash

# Scrap Yard Management System - Uninstall Script

echo "=== Scrap Yard Management System Uninstall ==="
echo "WARNING: This will permanently delete all data!"
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Uninstall cancelled."
    exit 0
fi

echo "Stopping services..."
sudo systemctl stop apache2

echo "Cleaning up supervisor processes..."
sudo supervisorctl stop scrapyard:* || true
sudo rm -f /etc/supervisor/conf.d/scrapyard.conf
sudo supervisorctl reread || true
sudo supervisorctl update || true

echo "Removing Apache configuration..."
sudo rm -f /etc/apache2/sites-available/scrapyard.conf
sudo rm -f /etc/apache2/sites-enabled/scrapyard.conf
sudo a2dissite scrapyard || true

echo "Dropping database and user..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS scrapyard_db;"
sudo -u postgres psql -c "DROP USER IF EXISTS scrapyard;"

echo "Removing application files..."
sudo rm -rf /var/www/scrapyard

echo "Removing system user..."
sudo userdel scrapyard || true

echo "Cleaning up systemd..."
sudo systemctl daemon-reload

echo "Restarting Apache..."
sudo systemctl restart apache2

echo "=== Uninstall Complete ==="
echo "All Scrap Yard Management System files, data, and users have been removed."