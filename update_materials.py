#!/usr/bin/env python3
import csv
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.material import Material

def update_materials_from_csv(csv_file_path):
    app = create_app()
    
    with app.app_context():
        updated_count = 0
        
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                code = row['COMMODITY CODE'].strip()
                description = row['TICKET DESCRIPTION'].strip()
                price = float(row['PRICE']) if row['PRICE'] else 0.0
                
                # Find existing material by code
                material = Material.query.filter_by(code=code).first()
                
                if material:
                    # Update existing material
                    material.price_per_pound = price
                    updated_count += 1
                    print(f"Updated {code}: {description} - ${price:.4f}/lb")
                else:
                    # Create new material if it doesn't exist
                    # Determine category based on code ranges
                    if code.startswith('1'):
                        if code.startswith('10'):
                            category = 'ALUMINUM'
                        elif code.startswith('11'):
                            category = 'ALLOYS'
                        elif code.startswith('12'):
                            category = 'CHARGES / PURCHASES'
                        elif code.startswith('13'):
                            category = 'FILMS'
                        elif code.startswith('14'):
                            category = 'STEEL - NO TARE'
                        else:
                            category = 'MISC'
                    elif code.startswith('2'):
                        category = 'BRASS'
                    elif code.startswith('3'):
                        category = 'COPPER'
                    elif code.startswith('4'):
                        category = 'LEAD'
                    elif code.startswith('5'):
                        category = 'TRUCK SCALE'
                    elif code.startswith('6'):
                        category = 'STAINLESS STEEL'
                    elif code.startswith('7'):
                        category = 'ELECTRONICS'
                    elif code.startswith('8'):
                        category = 'RADIATORS'
                    elif code.startswith('9'):
                        category = 'WIRE'
                    else:
                        category = 'ALUMINUM'
                    
                    # Determine if ferrous
                    ferrous_categories = ['TRUCK SCALE', 'STEEL - NO TARE', 'STAINLESS STEEL']
                    is_ferrous = category in ferrous_categories
                    
                    material = Material(
                        code=code,
                        description=description,
                        category=category,
                        is_ferrous=is_ferrous,
                        price_per_pound=price,
                        is_active=True
                    )
                    
                    db.session.add(material)
                    updated_count += 1
                    print(f"Created {code}: {description} - ${price:.4f}/lb")
        
        db.session.commit()
        print(f"\nTotal materials updated/created: {updated_count}")

if __name__ == '__main__':
    csv_file = r'C:\Users\david\Downloads\MaterialCSV_18082025082225.csv'
    update_materials_from_csv(csv_file)