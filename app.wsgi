#!/var/www/scrapyard/venv/bin/python3
import sys
import os

# Activate virtual environment
activate_this = '/var/www/scrapyard/venv/bin/activate_this.py'
if os.path.exists(activate_this):
    exec(open(activate_this).read(), dict(__file__=activate_this))

# Add the application directory to Python path
sys.path.insert(0, "/var/www/scrapyard/")

# Set environment variables
os.environ['FLASK_ENV'] = 'production'

from app import create_app

application = create_app()

if __name__ == "__main__":
    application.run()