from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user
from app import db

main_bp = Blueprint('main', __name__)

def require_permission(permission):
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if not current_user.has_permission(permission):
                abort(403)
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

@main_bp.route('/')
@login_required
def index():
    """Main dashboard with touch-screen interface"""
    from app.models.user import User
    from flask import redirect, url_for
    
    # Check if admin user has default password
    admin_user = User.query.filter_by(username='admin').first()
    if admin_user and admin_user.check_password('admin'):
        return redirect(url_for('auth.setup'))
    
    return render_template('dashboard.html', user=current_user)

@main_bp.route('/transaction')
@login_required
@require_permission('transaction')
def transaction():
    """Transaction processing page"""
    return render_template('transaction.html')

@main_bp.route('/cashier')
@login_required
@require_permission('transaction')
def cashier_dashboard():
    """Cashier point of sale dashboard"""
    from app.models.material import Material
    materials = Material.query.filter_by(is_active=True).order_by(Material.category, Material.description).all()
    return render_template('cashier_dashboard.html', materials=materials)

@main_bp.route('/api/weight/<int:scale_id>')
@login_required
def get_weight(scale_id):
    """Get current weight from specified scale"""
    return jsonify({'weight': 0.0, 'stable': False, 'unit': 'lbs'})

@main_bp.route('/api/capture/<int:camera_id>')
@login_required
def capture_photo(camera_id):
    """Capture photo from specified camera"""
    return jsonify({'success': True, 'photo': 'base64_data_here'})

@main_bp.route('/api/print_receipt', methods=['POST'])
@login_required
def print_receipt():
    """Print transaction receipt"""
    return jsonify({'success': True})

@main_bp.route('/api/customers/create', methods=['POST'])
@login_required
@require_permission('customer_lookup')
def create_customer():
    """Create new customer"""
    from app.models.customer import Customer
    import os
    
    try:
        name = request.form.get('name')
        if not name:
            flash('Name is required')
            return redirect(url_for('main.customer_lookup'))
        street_address = request.form.get('street_address', '')
        city = request.form.get('city', '')
        state = request.form.get('state', '')
        zip_code = request.form.get('zip_code', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        license_number = request.form.get('drivers_license_number', '')
        
        # Combine address fields into single address
        address = f"{street_address} {city} {state} {zip_code}".strip()
        
        customer = Customer(
            name=name,
            address=address,
            phone=phone,
            email=email,
            drivers_license_number=license_number
        )
        
        # Handle license photo upload
        if 'license_photo' in request.files:
            file = request.files['license_photo']
            if file and file.filename:
                # Create customer photos directory
                photo_dir = '/var/www/scrapyard/static/customer_photos'
                os.makedirs(photo_dir, exist_ok=True)
                
                # Generate secure filename
                import uuid
                from werkzeug.utils import secure_filename
                safe_filename = secure_filename(file.filename) or "upload.jpg"
                ext = safe_filename.rsplit('.', 1)[1].lower() if '.' in safe_filename else 'jpg'
                if ext not in ['jpg', 'jpeg', 'png', 'gif']:
                    ext = 'jpg'
                filename = f"license_{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(photo_dir, filename)
                
                # Validate path to prevent traversal
                if not filepath.startswith(photo_dir):
                    return jsonify({'success': False, 'error': 'Invalid file path'}), 400
                
                file.save(filepath)
                customer.drivers_license_photo = filename
        
        db.session.add(customer)
        db.session.commit()
        
        return jsonify({'success': True, 'customer_id': customer.id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/customers/search')
@login_required
@require_permission('customer_lookup')
def search_customers():
    """Search customers by name or license number"""
    from app.models.customer import Customer
    
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify({'customers': []})
    
    customers = Customer.query.filter(
        db.or_(
            Customer.name.ilike(f'%{query}%'),
            Customer.drivers_license_number.ilike(f'%{query}%')
        ),
        Customer.is_active == True
    ).limit(10).all()
    
    results = []
    for customer in customers:
        results.append({
            'id': customer.id,
            'name': customer.name,
            'address': customer.address,
            'phone': customer.phone,
            'drivers_license_number': customer.drivers_license_number
        })
    
    return jsonify({'customers': results})

@main_bp.route('/api/camera/capture', methods=['POST'])
@login_required
def capture_camera_photo():
    """Capture photo using available camera"""
    from app.models.device import Device
    from app.services.camera_service import AxisCameraService
    
    # Find first available camera
    camera = Device.query.filter_by(device_type='camera', is_active=True).first()
    
    if not camera:
        return jsonify({'success': False, 'error': 'No camera available'})
    
    try:
        service = AxisCameraService(camera.ip_address)
        image_data = service.capture_image()
        
        if image_data:
            # Save captured image
            import os, uuid
            photo_dir = '/var/www/scrapyard/static/captures'
            os.makedirs(photo_dir, exist_ok=True)
            
            filename = f"capture_{uuid.uuid4().hex}.jpg"
            filepath = os.path.join(photo_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            return jsonify({'success': True, 'filename': filename})
        else:
            return jsonify({'success': False, 'error': 'Failed to capture image'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/customer_lookup')
@login_required
@require_permission('customer_lookup')
def customer_lookup():
    """Customer lookup and ID scanning page"""
    return render_template('customer_lookup.html')

@main_bp.route('/reports')
@login_required
@require_permission('reports')
def reports():
    """Reports and analytics page"""
    return render_template('reports.html')

@main_bp.route('/materials')
@login_required
def materials():
    """Materials management page - accessible to cashiers and admins"""
    if not (current_user.has_permission('transaction') or current_user.is_admin):
        abort(403)
    
    from app.models.material import Material
    materials = Material.query.order_by(Material.category, Material.code).all()
    return render_template('materials.html', materials=materials)

@main_bp.route('/api/materials/update/<int:material_id>', methods=['POST'])
@login_required
def update_material_price(material_id):
    """Update material price - accessible to cashiers and admins"""
    if not (current_user.has_permission('transaction') or current_user.is_admin):
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    
    from app.models.material import Material
    try:
        material = Material.query.get_or_404(material_id)
        data = request.get_json()
        
        if 'price_per_pound' in data:
            material.price_per_pound = float(data['price_per_pound'])
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Price required'}), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Update failed'}), 500

@main_bp.route('/api/customers/list')
@login_required
@require_permission('customer_lookup')
def list_customers():
    """Get customers with pagination"""
    from app.models.customer import Customer
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name).limit(per_page).offset((page-1)*per_page).all()
    
    results = []
    for customer in customers:
        results.append({
            'id': customer.id,
            'name': customer.name,
            'address': customer.address,
            'phone': customer.phone,
            'drivers_license_number': customer.drivers_license_number
        })
    
    return jsonify({'customers': results})

@main_bp.route('/api/customers/<int:customer_id>')
@login_required
@require_permission('customer_lookup')
def get_customer(customer_id):
    """Get single customer details"""
    from app.models.customer import Customer
    
    customer = Customer.query.get_or_404(customer_id)
    
    return jsonify({
        'customer': {
            'id': customer.id,
            'name': customer.name,
            'address': customer.address,
            'phone': customer.phone,
            'email': customer.email,
            'drivers_license_number': customer.drivers_license_number
        }
    })

@main_bp.route('/api/customers/update/<int:customer_id>', methods=['POST'])
@login_required
@require_permission('customer_lookup')
def update_customer(customer_id):
    """Update customer details"""
    from app.models.customer import Customer
    import os
    
    try:
        customer = Customer.query.get_or_404(customer_id)
        
        customer.name = request.form['name']
        customer.address = f"{request.form.get('street_address', '')} {request.form.get('city', '')} {request.form.get('state', '')} {request.form.get('zip_code', '')}".strip()
        customer.phone = request.form.get('phone', '')
        customer.email = request.form.get('email', '')
        customer.drivers_license_number = request.form.get('drivers_license_number', '')
        
        # Handle license photo upload
        if 'license_photo' in request.files:
            file = request.files['license_photo']
            if file and file.filename:
                photo_dir = '/var/www/scrapyard/static/customer_photos'
                os.makedirs(photo_dir, exist_ok=True)
                
                import uuid
                filename = f"license_{uuid.uuid4().hex}.jpg"
                filepath = os.path.join(photo_dir, filename)
                
                file.save(filepath)
                customer.drivers_license_photo = filename
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500