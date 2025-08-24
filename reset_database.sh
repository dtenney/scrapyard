#!/bin/bash

set -e  # Exit on any command failure

# Reset Database - Drop everything and recreate

echo "=== Resetting Database ==="

# Drop database and user
echo "Dropping database and user..."
if ! sudo -u postgres psql -c "DROP DATABASE IF EXISTS scrapyard_db;"; then
    echo "Error: Failed to drop database"
    exit 1
fi

if ! sudo -u postgres psql -c "DROP USER IF EXISTS scrapyard;"; then
    echo "Error: Failed to drop user"
    exit 1
fi

# Recreate database and user
echo "Creating fresh database and user..."
if ! sudo -u postgres createuser scrapyard; then
    echo "Error: Failed to create user"
    exit 1
fi

if ! sudo -u postgres createdb scrapyard_db -O scrapyard; then
    echo "Error: Failed to create database"
    exit 1
fi

DB_PASSWORD=${SCRAPYARD_DB_PASSWORD:-$(openssl rand -base64 32)}
if ! sudo -u postgres psql -c "ALTER USER scrapyard PASSWORD '$DB_PASSWORD';"; then
    echo "Error: Failed to set password"
    exit 1
fi
echo "Database password set from environment variable"

echo "Database reset complete"