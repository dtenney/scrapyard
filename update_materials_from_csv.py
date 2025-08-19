#!/usr/bin/env python3
"""
Update materials database from CSV file
"""
import os
import sys
import csv
from decimal import Decimal

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models.material import Material

def update_materials_from_csv():
    """Replace materials database with CSV data"""
    app = create_app()
    
    with app.app_context():
        try:
            # Clear existing materials
            Material.query.delete()
            
            # Read CSV file
            csv_path = r'C:\Users\david\Downloads\Materials20250819.csv'
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                
                for row in reader:
                    code = row['Code'].strip()
                    description = row['Description'].strip()
                    our_price = float(row['Our Price']) if row['Our Price'] else 0.0
                    category = row['Category'].strip()
                    material_type = row['Type'].strip()
                    
                    # Determine if ferrous based on type
                    is_ferrous = material_type == 'Ferrous'
                    
                    material = Material(
                        code=code,
                        description=description,
                        category=category,
                        is_ferrous=is_ferrous,
                        price_per_pound=our_price
                    )
                    
                    db.session.add(material)
                    count += 1
                
                db.session.commit()
                print(f"✓ Successfully loaded {count} materials from CSV")
                return True
                
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error updating materials: {e}")
            return False

if __name__ == '__main__':
    success = update_materials_from_csv()
    sys.exit(0 if success else 1)