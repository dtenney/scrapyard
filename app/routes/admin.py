from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.user import User, UserGroup
from app.models.device import Device
from app import db

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@login_required
def require_admin():
    if not current_user.is_admin:
        return redirect(url_for('main.index'))

@admin_bp.route('/')
def index():
    return render_template('admin/dashboard.html')

@admin_bp.route('/users')
def users():
    users = User.query.all()
    groups = UserGroup.query.all()
    return render_template('admin/users.html', users=users, groups=groups)

@admin_bp.route('/users/create', methods=['POST'])
def create_user():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    
    user = User(username=username, email=email)
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    flash('User created successfully')
    return redirect(url_for('admin.users'))

@admin_bp.route('/devices')
def devices():
    devices = Device.query.all()
    return render_template('admin/devices.html', devices=devices)

@admin_bp.route('/devices/create', methods=['POST'])
def create_device():
    data = request.get_json()
    
    device = Device(
        name=data['name'],
        device_type=data['device_type'],
        ip_address=data['ip_address'],
        port=data.get('port'),
        model=data.get('model'),
        config=data.get('config', {})
    )
    
    db.session.add(device)
    db.session.commit()
    
    return jsonify({'success': True, 'device_id': device.id})

@admin_bp.route('/groups')
def groups():
    groups = UserGroup.query.all()
    return render_template('admin/groups.html', groups=groups)

@admin_bp.route('/materials')
def materials():
    from app.models.material import Material
    materials = Material.query.order_by(Material.category, Material.code).all()
    return render_template('admin/materials.html', materials=materials)

@admin_bp.route('/materials/create', methods=['POST'])
def create_material():
    from app.models.material import Material
    data = request.get_json()
    
    material = Material(
        code=data['code'],
        description=data['description'],
        category=data['category'],
        price_per_pound=data.get('price_per_pound', 0.0)
    )
    
    db.session.add(material)
    db.session.commit()
    
    return jsonify({'success': True, 'material_id': material.id})

@admin_bp.route('/materials/update/<int:material_id>', methods=['POST'])
def update_material(material_id):
    from app.models.material import Material
    material = Material.query.get_or_404(material_id)
    data = request.get_json()
    
    material.code = data['code']
    material.description = data['description']
    material.category = data['category']
    material.price_per_pound = data.get('price_per_pound', 0.0)
    
    db.session.commit()
    
    return jsonify({'success': True})

@admin_bp.route('/materials/load_csv', methods=['POST'])
def load_materials_csv():
    from app.models.material import Material
    import csv
    import io
    
    # CSV data from materialMigration.csv
    csv_data = '''Code,Description,GropDescription
"101","SHEET","ALUMINUM"
"102","CAST ALUM","ALUMINUM"
"103","DIECAST ALUM","ALUMINUM"
"201","YELLOW BRASS CLEAN","BRASS"
"202","YELLOW BRASS DIRTY","BRASS"
"301","BARE BRIGHT","COPPER"
"302","#1 COPPER","COPPER"
"401","SOFT LEAD","LEAD"
"501","LIGHT STEEL","TRUCK SCALE"
"601","304 CLEAN STAINLESS","STAINLESS STEEL"
"701","COMPUTER - WHOLE","ELECTRONICS"
"801","ALUM RAD CLEAN","RADIATORS"
"901","HAIR WIRE","WIRE"'''
    
    reader = csv.DictReader(io.StringIO(csv_data))
    count = 0
    
    for row in reader:
        code = row['Code'].strip('"')
        description = row['Description'].strip('"')
        category = row['GropDescription'].strip('"')
        
        # Skip if material already exists
        if Material.query.filter_by(code=code).first():
            continue
            
        material = Material(
            code=code,
            description=description,
            category=category,
            price_per_pound=0.0000
        )
        
        db.session.add(material)
        count += 1
    
    db.session.commit()
    return jsonify({'success': True, 'count': count})