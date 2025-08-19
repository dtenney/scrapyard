#!/usr/bin/env python3
"""
Scrap Yard Management System
Flask application entry point
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    import os
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))
    app.run(debug=debug, host=host, port=port)