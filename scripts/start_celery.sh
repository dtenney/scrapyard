#!/bin/bash

# Start Celery worker and beat scheduler for price updates

cd /var/www/scrapyard

# Start Celery worker in background
./venv/bin/celery -A app.celery_app worker --loglevel=info --detach

# Start Celery beat scheduler for periodic tasks
./venv/bin/celery -A app.celery_app beat --loglevel=info --detach

echo "Celery worker and beat scheduler started"