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
    return render_template('dashboard.html', user=current_user)

@main_bp.route('/transaction')
@login_required
@require_permission('transaction')
def transaction():
    """Transaction processing page"""
    return render_template('transaction.html')

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
        name = request.form['name']
        address = request.form.get('address', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        license_number = request.form.get('drivers_license_number', '')
        
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
                
                # Generate filename
                import uuid
                filename = f"license_{uuid.uuid4().hex}.jpg"
                filepath = os.path.join(photo_dir, filename)
                
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