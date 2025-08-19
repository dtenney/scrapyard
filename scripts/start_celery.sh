#!/bin/bash

set -e

# Start Celery worker and beat scheduler for price updates

if ! cd /var/www/scrapyard; then
    echo "Error: Cannot change to /var/www/scrapyard directory"
    exit 1
fi

# Start Celery worker in background
if ! ./venv/bin/celery -A celery_worker worker --loglevel=info --detach; then
    echo "Error: Failed to start Celery worker"
    exit 1
fi

# Start Celery beat scheduler for periodic tasks
if ! ./venv/bin/celery -A celery_worker beat --loglevel=info --detach; then
    echo "Error: Failed to start Celery beat scheduler"
    exit 1
fi

echo "Celery worker and beat scheduler started"