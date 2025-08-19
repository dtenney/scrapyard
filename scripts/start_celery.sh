#!/bin/bash

# Start Celery worker and beat scheduler for price updates

cd /var/www/scrapyard

# Start Celery worker in background
./venv/bin/celery -A celery_worker worker --loglevel=info --detach

# Start Celery beat scheduler for periodic tasks
./venv/bin/celery -A celery_worker beat --loglevel=info --detach

echo "Celery worker and beat scheduler started"