#!/usr/bin/python3
import sys
import os

# Add the application directory to Python path
sys.path.insert(0, "/var/www/scrapyard/")

# Set environment variables
os.environ['FLASK_ENV'] = 'production'

from app import create_app

application = create_app()

if __name__ == "__main__":
    application.run()