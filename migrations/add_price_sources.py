#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '/var/www/scrapyard')

from app import create_app, db
from app.models.price_source import PriceSource

def create_price_sources_table():
    """Create price_sources table and add default SGT Scrap source"""
    app = create_app()
    
    with app.app_context():
        try:
            # Create the table
            db.create_all()
            
            # Add default SGT Scrap source
            existing = PriceSource.query.filter_by(name='SGT Scrap').first()
            if not existing:
                sgt_source = PriceSource(
                    name='SGT Scrap',
                    url='https://sgt-scrap.com/todays-prices/',
                    is_active=True
                )
                db.session.add(sgt_source)
                db.session.commit()
                print("Added default SGT Scrap price source")
            
            print("Price sources table created successfully")
            
        except Exception as e:
            print(f"Error creating price sources table: {e}")
            db.session.rollback()

if __name__ == '__main__':
    create_price_sources_table()