from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user
from app import db
import logging

logger = logging.getLogger(__name__)

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
    try:
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user and admin_user.check_password('admin'):
            return redirect(url_for('auth.setup'))
    except Exception as e:
        logger.error("Database error checking admin user: %s", str(e)[:100])
        # Continue with normal flow if database check fails
    
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
    # TODO: Implement actual scale integration
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
        
        customer = Customer(
            name=name,
            street_address=street_address,
            city=city,
            state=state,
            zip_code=zip_code,
            phone=phone,
            email=email,
            drivers_license_number=license_number
        )
        
        db.session.add(customer)
        db.session.flush()  # Get customer ID
        
        # Handle license photo upload using PhotoService
        if 'license_photo' in request.files:
            file = request.files['license_photo']
            if file and file.filename:
                from app.services.photo_service import PhotoService
                relative_path, error = PhotoService.save_customer_photo(customer.id, file)
                if error:
                    db.session.rollback()
                    return jsonify({'success': False, 'error': error}), 400
                customer.drivers_license_photo_path = relative_path
                customer.drivers_license_photo_filename = file.filename
        
        db.session.commit()
        
        return jsonify({'success': True, 'customer_id': customer.id})
        
    except Exception as e:
        db.session.rollback()
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
Customer.is_active.is_(True)
    ).limit(10).all()
    
    results = []
    for customer in customers:
        results.append({
            'id': customer.id,
            'name': customer.name,
            'address': customer.full_address,
            'phone': customer.phone,
            'drivers_license_number': customer.drivers_license_number
        })
    
    return jsonify({'customers': results})





@main_bp.route('/api/camera/ping')
def ping_test():
    """Basic route test - no auth required"""
    return jsonify({'status': 'alive', 'timestamp': str(__import__('datetime').datetime.now())})











@main_bp.route('/api/camera/stream')
@login_required
def camera_stream():
    """Proxy MJPEG stream from camera"""
    from app.models.device import Device
    from app.services.camera_service import AxisCameraService
    from flask import Response
    import requests
    
    # Find first available camera
    camera = Device.query.filter_by(device_type='camera', is_active=True).first()
    
    if not camera:
        return Response('No camera available', status=404)
    
    try:
        service = AxisCameraService(camera.ip_address)
        stream_url = service.get_stream_url()
        
        def generate():
            try:
                response = requests.get(stream_url, stream=True, timeout=30)
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        yield chunk
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield b''
        
        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
        
    except Exception as e:
        logger.error(f"Camera stream error: {e}")
        return Response('Camera unavailable', status=503)

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
            from werkzeug.utils import secure_filename
            photo_dir = '/var/www/scrapyard/static/captures'
            os.makedirs(photo_dir, exist_ok=True)
            
            filename = f"capture_{uuid.uuid4().hex}.jpg"
            safe_filename = secure_filename(filename)
            filepath = os.path.join(photo_dir, safe_filename)
            
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            return jsonify({'success': True, 'filename': filename})
        else:
            return jsonify({'success': False, 'error': 'Failed to capture image'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/api/ocr/extract_license', methods=['POST'])
@login_required
def extract_license_data():
    """Extract data from driver's license photo using OCR"""
    try:
        from app.services.license_ocr_service import LicenseOCRService
    except ImportError as e:
        return jsonify({'success': False, 'error': 'OCR dependencies not installed'})
    
    import tempfile
    import os
    
    if 'license_photo' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['license_photo']
    if not file.filename:
        return jsonify({'success': False, 'error': 'No file selected'})
    
    try:
        # Save file temporarily for OCR processing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            file.save(temp_file.name)
            
            # Extract data using OCR
            result = LicenseOCRService.extract_license_data(temp_file.name)
            
            # Clean up temp file
            os.unlink(temp_file.name)
            
            return jsonify(result)
            
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
    """Materials management page"""
    if not (current_user.has_permission('transaction') or current_user.is_admin):
        abort(403)
    
    from app.models.material import Material
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    query = Material.query
    
    if search:
        query = query.filter(
            db.or_(
                Material.code.ilike(f'%{search}%'),
                Material.description.ilike(f'%{search}%'),
                Material.category.ilike(f'%{search}%')
            )
        )
    
    pagination = query.order_by(Material.category, Material.code).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('materials.html', 
                         materials=pagination.items, 
                         pagination=pagination,
                         search=search)

@main_bp.route('/materials/create', methods=['POST'])
@login_required
def create_material():
    """Create new material"""
    if not (current_user.has_permission('transaction') or current_user.is_admin):
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
    from app.models.material import Material
    try:
        data = request.get_json()
        if not data or 'code' not in data or 'description' not in data:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        material = Material(
            code=data['code'],
            description=data['description'],
            category=data.get('category', ''),
            is_ferrous=data.get('is_ferrous', 'false').lower() == 'true',
            price_per_pound=data.get('price_per_pound', 0.0)
        )
        
        db.session.add(material)
        db.session.commit()
        
        return jsonify({'success': True, 'material_id': material.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Database error'}), 500

@main_bp.route('/materials/<int:material_id>')
@login_required
def get_material(material_id):
    """Get material details"""
    if not (current_user.has_permission('transaction') or current_user.is_admin):
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
    from app.models.material import Material
    try:
        material = Material.query.get_or_404(material_id)
        return jsonify({
            'success': True,
            'material': {
                'id': material.id,
                'code': material.code,
                'description': material.description,
                'category': material.category,
                'is_ferrous': material.is_ferrous,
                'price_per_pound': float(material.price_per_pound),
                'is_active': material.is_active
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/materials/update/<int:material_id>', methods=['POST'])
@login_required
def update_material(material_id):
    """Update material details"""
    if not (current_user.has_permission('transaction') or current_user.is_admin):
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
    from app.models.material import Material
    try:
        material = Material.query.get_or_404(material_id)
        data = request.get_json()
        
        if not data or 'code' not in data or 'description' not in data:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        material.code = data['code']
        material.description = data['description']
        material.category = data['category']
        material.is_ferrous = data.get('is_ferrous', 'false').lower() == 'true'
        material.price_per_pound = data.get('price_per_pound', 0.0)
        material.is_active = data.get('is_active', 'true').lower() == 'true'
        
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Database error'}), 500

@main_bp.route('/materials/update_prices', methods=['POST'])
@login_required
def update_prices():
    """Update prices from SGT Scrap website"""
    if not (current_user.has_permission('transaction') or current_user.is_admin):
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
    from app.services.sgt_scraper import SGTScraper
    
    try:
        scraper = SGTScraper()
        updated_count = scraper.update_material_prices()
        return jsonify({'success': True, 'updated': updated_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



@main_bp.route('/api/customers/list')
@login_required
@require_permission('customer_lookup')
def list_customers():
    """Get customers with pagination and search"""
    from app.models.customer import Customer
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    per_page = 50
    
    query = Customer.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            db.or_(
                Customer.name.ilike(f'%{search}%'),
                Customer.phone.ilike(f'%{search}%'),
                Customer.drivers_license_number.ilike(f'%{search}%')
            )
        )
    
    pagination = query.order_by(Customer.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    results = []
    for customer in pagination.items:
        results.append({
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone or '',
            'drivers_license_number': customer.drivers_license_number or '',
            'city': customer.city or '',
            'state': customer.state or ''
        })
    
    return jsonify({
        'customers': results,
        'pagination': {
            'page': pagination.page,
            'pages': pagination.pages,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next
        }
    })

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
            'street_address': customer.street_address,
            'city': customer.city,
            'state': customer.state,
            'zip_code': customer.zip_code,
            'phone': customer.phone,
            'email': customer.email,
            'drivers_license_number': customer.drivers_license_number,
            'drivers_license_photo_path': customer.drivers_license_photo_path
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
        customer.street_address = request.form.get('street_address', '')
        customer.city = request.form.get('city', '')
        customer.state = request.form.get('state', '')
        customer.zip_code = request.form.get('zip_code', '')
        customer.phone = request.form.get('phone', '')
        customer.email = request.form.get('email', '')
        customer.drivers_license_number = request.form.get('drivers_license_number', '')
        
        # Handle license photo upload using PhotoService
        if 'license_photo' in request.files:
            file = request.files['license_photo']
            if file and file.filename:
                from app.services.photo_service import PhotoService
                
                # Delete old photo if it exists
                if customer.drivers_license_photo_path:
                    PhotoService.delete_photo(customer.drivers_license_photo_path)
                
                relative_path, error = PhotoService.save_customer_photo(customer.id, file)
                if error:
                    return jsonify({'success': False, 'error': error}), 400
                customer.drivers_license_photo_path = relative_path
                customer.drivers_license_photo_filename = file.filename
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500