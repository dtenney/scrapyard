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
                from werkzeug.utils import safe_join
                try:
                    safe_filepath = safe_join(photo_dir, filename)
                    if safe_filepath is None:
                        return jsonify({'success': False, 'error': 'Invalid file path'}), 400
                    filepath = safe_filepath
                except ValueError:
                    return jsonify({'success': False, 'error': 'Invalid file path'}), 400
                
                file.save(filepath)
                customer.drivers_license_photo = filename
        
        db.session.add(customer)
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
        Customer.is_active == True
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

@main_bp.route('/camera_stream')
@login_required
def camera_stream():
    """Camera stream viewing page"""
    if not (current_user.has_permission('transaction') or current_user.is_admin):
        abort(403)
    return render_template('camera_stream.html')

@main_bp.route('/api/camera/cors-test')
@login_required
def cors_test():
    """Test CORS by making server-side request to camera"""
    import requests
    from requests.auth import HTTPBasicAuth
    
    try:
        response = requests.get(
            'http://10.0.10.39/axis-cgi/mjpg/video.cgi?camera=1&resolution=640x480',
            auth=HTTPBasicAuth('admin', 'admin'),
            timeout=3,
            stream=False
        )
        return jsonify({
            'server_can_access': True,
            'status_code': response.status_code,
            'content_type': response.headers.get('Content-Type', 'unknown'),
            'cors_issue': response.status_code == 200
        })
    except Exception as e:
        return jsonify({
            'server_can_access': False,
            'error': str(e),
            'cors_issue': False
        })

@main_bp.route('/api/camera/ping')
def ping_test():
    """Basic route test - no auth required"""
    return jsonify({'status': 'alive', 'server': '10.0.10.178', 'timestamp': str(__import__('datetime').datetime.now())})

@main_bp.route('/api/camera/stream')
@login_required
def camera_stream_proxy():
    """Actual streaming proxy"""
    import requests
    from flask import Response
    from requests.auth import HTTPBasicAuth
    
    try:
        response = requests.get(
            'http://10.0.10.39/axis-cgi/mjpg/video.cgi?resolution=640x480',
            auth=HTTPBasicAuth('admin', 'admin'),
            stream=True,
            timeout=5
        )
        
        if response.status_code != 200:
            return f'Camera returned {response.status_code}', response.status_code
        
        def generate():
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    yield chunk
        
        return Response(
            generate(),
            mimetype='multipart/x-mixed-replace'
        )
        
    except Exception as e:
        return f'Stream error: {str(e)}', 500

@main_bp.route('/api/camera/simple')
@login_required
def simple_camera_test():
    """Test if server can reach camera at all"""
    import subprocess
    import socket
    
    results = {}
    
    # Test ping from server to camera
    try:
        result = subprocess.run(['ping', '-c', '1', '10.0.10.39'], 
                              capture_output=True, text=True, timeout=5)
        results['ping'] = 'SUCCESS' if result.returncode == 0 else 'FAILED'
        results['ping_output'] = result.stdout[:200]
    except Exception as e:
        results['ping'] = f'ERROR: {e}'
    
    # Test TCP connection to port 80
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('10.0.10.39', 80))
        sock.close()
        results['tcp_80'] = 'OPEN' if result == 0 else 'CLOSED'
    except Exception as e:
        results['tcp_80'] = f'ERROR: {e}'
    
    # Test basic HTTP
    try:
        import requests
        response = requests.get('http://10.0.10.39/', timeout=3)
        results['http'] = f'SUCCESS - {response.status_code}'
    except Exception as e:
        results['http'] = f'FAILED: {e}'
    
    return jsonify(results)

@main_bp.route('/api/camera/debug')
@login_required
def debug_camera():
    """Test camera credentials"""
    import requests
    from requests.auth import HTTPBasicAuth
    
    results = []
    
    # Test common credentials
    credentials = [
        ('admin', 'admin'),
        ('root', 'dialog'),
        ('admin', 'password'),
        ('admin', ''),
        ('user', 'user'),
        ('viewer', 'viewer'),
        ('', ''),
        ('axis', 'axis')
    ]
    
    for username, password in credentials:
        try:
            auth = HTTPBasicAuth(username, password) if username or password else None
            response = requests.get(
                'http://10.0.10.39/axis-cgi/mjpg/video.cgi?resolution=640x480',
                auth=auth,
                timeout=2
            )
            results.append(f"{username}:{password} -> {response.status_code}")
            if response.status_code == 200:
                results.append(f"*** WORKING CREDENTIALS: {username}:{password} ***")
        except requests.exceptions.Timeout:
            logger.error(f"Timeout testing {username}:{password}")
            results.append(f"{username}:{password} -> TIMEOUT")
        except Exception as e:
            logger.error(f"Error testing {username}:{password}: {e}")
            results.append(f"{username}:{password} -> ERROR: {e}")
    
    return jsonify({'debug_results': results})

@main_bp.route('/api/camera/test')
@login_required
def test_camera_connection():
    """Test camera connection with multiple credentials"""
    import requests
    from requests.auth import HTTPBasicAuth
    import socket
    
    # Test basic network connectivity first
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('10.0.10.39', 80))
        sock.close()
        network_reachable = result == 0
    except Exception as net_error:
        network_reachable = False
        logger.error(f"Network test failed: {net_error}")
    
    # Test without auth first
    try:
        logger.info("Testing camera without authentication")
        response = requests.get(
            'http://10.0.10.39/axis-cgi/mjpg/video.cgi?camera=1&resolution=640x480',
            timeout=5
        )
        if response.status_code != 401:
            return jsonify({
                'success': True,
                'status_code': response.status_code,
                'accessible': True,
                'working_credentials': 'no_auth_required',
                'network_reachable': network_reachable
            })
    except Exception as e:
        logger.info(f"No auth test failed: {e}")
    
    # Try common credentials
    credentials = [
        ('root', 'dialog'),
        ('admin', 'admin'),
        ('viewer', 'viewer'),
        ('user', 'user'),
        ('', ''),
        ('admin', ''),
        ('root', '')
    ]
    
    for username, password in credentials:
        try:
            logger.info(f"Testing camera with credentials: {username}:{password}")
            response = requests.get(
                'http://10.0.10.39/axis-cgi/param.cgi?action=list&group=Properties.System',
                auth=HTTPBasicAuth(username, password) if username or password else None,
                timeout=5
            )
            if response.status_code == 200:
                logger.info(f"Camera accessible with {username}:{password}")
                return jsonify({
                    'success': True,
                    'status_code': response.status_code,
                    'accessible': True,
                    'working_credentials': f'{username}:{password}',
                    'network_reachable': network_reachable
                })
            else:
                logger.info(f"Credentials {username}:{password} failed: {response.status_code}")
        except requests.exceptions.Timeout:
            logger.error(f"Timeout testing {username}:{password}")
        except Exception as e:
            logger.error(f"Error testing {username}:{password}: {e}")
    
    return jsonify({
        'success': False,
        'error': 'All credential combinations failed',
        'accessible': False,
        'network_reachable': network_reachable
    })

@main_bp.route('/api/camera/proxy')
@login_required
def camera_proxy():
    """Test camera connection without streaming"""
    import requests
    from requests.auth import HTTPBasicAuth
    
    logger.info("Camera proxy test accessed")
    
    try:
        response = requests.get(
            'http://10.0.10.39/',
            timeout=3
        )
        return f'<html><body><h3>Camera Test</h3><p>Camera root page: {response.status_code}</p><p>Server can reach camera</p></body></html>'
        
    except Exception as e:
        logger.error(f"Camera test error: {e}")
        return f'<html><body><h3>Camera Test Failed</h3><p>Error: {str(e)}</p><p>Server cannot reach camera</p></body></html>'

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
            category=data['category'],
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
        customer.street_address = request.form.get('street_address', '')
        customer.city = request.form.get('city', '')
        customer.state = request.form.get('state', '')
        customer.zip_code = request.form.get('zip_code', '')
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
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500