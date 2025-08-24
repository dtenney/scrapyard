#!/usr/bin/env python3
"""
Development setup script for Windows
Creates database tables and initializes data
"""

import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def setup_database():
    """Initialize database for development"""
    try:
        from app import create_app, db
        from app.models.user import User, UserGroup, UserGroupMember
        from app.models.device import Device
        from app.models.material import Material
        from app.models.customer import Customer
        from app.models.permissions import Permission, GroupPermission
        from app.services.setup_service import initialize_default_groups
        
        app = create_app()
        with app.app_context():
            print("Creating database tables...")
            db.create_all()
            
            print("Initializing default groups...")
            initialize_default_groups()
            
            print("Loading materials from CSV...")
            load_materials()
            
            print("Database setup complete!")
            
    except Exception as e:
        print(f"Database setup failed: {e}")
        return False
    
    return True

def load_materials():
    """Load materials from CSV data"""
    from app import db
    from app.models.material import Material
    import csv
    import io
    
    csv_data = '''Code,Description,Our Price,Category,Type
101,SHEET,0.55,ALUMINUM,Non-Ferrous
102,CAST ALUM,0.48,ALUMINUM,Non-Ferrous
201,YELLOW BRASS CLEAN,2.4,BRASS,Non-Ferrous
301,BARE BRIGHT,3.88,COPPER,Non-Ferrous
401,SOFT LEAD,0.46,LEAD,Non-Ferrous
501,LIGHT STEEL,0.0675,TRUCK SCALE,Ferrous
601,304 CLEAN STAINLESS,0.25,STAINLESS STEEL,Ferrous
701,COMPUTER - WHOLE,0.18,ELECTRONICS,Non-Ferrous
801,ALUM RAD CLEAN,0.4,RADIATORS,Non-Ferrous
901,HAIR WIRE,3.1,WIRE,Non-Ferrous'''
    
    reader = csv.DictReader(io.StringIO(csv_data))
    count = 0
    
    for row in reader:
        code = row['Code'].strip()
        description = row['Description'].strip()
        our_price = float(row['Our Price']) if row['Our Price'] else 0.0
        category = row['Category'].strip()
        material_type = row['Type'].strip()
        
        is_ferrous = material_type == 'Ferrous'
        
        # Check if material already exists
        existing = Material.query.filter_by(code=code).first()
        if not existing:
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
    print(f'Materials loaded: {count} items')

def create_upload_dirs():
    """Create upload directories"""
    upload_dirs = [
        'uploads/customer_photos',
        'uploads/logos'
    ]
    
    for dir_path in upload_dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"Created directory: {dir_path}")

if __name__ == '__main__':
    print("=== Development Setup ===")
    
    # Create upload directories
    create_upload_dirs()
    
    # Setup database
    if setup_database():
        print("Setup completed successfully!")
    else:
        print("Setup failed!")
        sys.exit(1)