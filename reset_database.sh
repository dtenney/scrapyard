#!/bin/bash

# Reset Database - Drop everything and recreate

echo "=== Resetting Database ==="

# Drop database and user
echo "Dropping database and user..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS scrapyard_db;"
sudo -u postgres psql -c "DROP USER IF EXISTS scrapyard;"

# Recreate database and user
echo "Creating fresh database and user..."
sudo -u postgres createuser scrapyard
sudo -u postgres createdb scrapyard_db -O scrapyard
sudo -u postgres psql -c "ALTER USER scrapyard PASSWORD 'scrapyard123';"

echo "Database reset complete"