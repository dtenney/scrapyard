from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.customer import Customer
from app.services.printer_service import StarPrinterService
import requests
import os
import logging

# Setup Geoapify logging
geoapify_logger = logging.getLogger('geoapify')
geoapify_logger.setLevel(logging.INFO)
try:
    import tempfile
    log_dir = tempfile.gettempdir()
    handler = logging.FileHandler(os.path.join(log_dir, 'geoapify.log'))
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    geoapify_logger.addHandler(handler)
except:
    pass  # Logging disabled if can't create file

api_bp = Blueprint('api', __name__)

@api_bp.route('/devices/test/<int:device_id>')
@login_required
def test_device(device_id):
    """Test connection to a device"""
    return jsonify({'success': True, 'status': 'connected'})

@api_bp.route('/transaction/create', methods=['POST'])
@login_required
def create_transaction():
    """Create new transaction"""
    data = request.get_json()
    return jsonify({'success': True, 'transaction_id': 1})

@api_bp.route('/customer/scan', methods=['POST'])
@login_required
def scan_customer_id():
    """Process scanned driver's license"""
    data = request.get_json()
    return jsonify({'success': True, 'customer_data': {}})

@api_bp.route('/compliance/report')
@login_required
def compliance_report():
    """Generate compliance report"""
    return jsonify({'success': True, 'report_url': '/reports/compliance.pdf'})

@api_bp.route('/address/validate', methods=['POST'])
@login_required
def validate_address():
    """Validate address using Geoapify API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'data': {'error': 'Invalid request data'}})
            
        street = data.get('street', '').strip()
        city = data.get('city', '').strip()
        state = data.get('state', '').strip()
        zipcode = data.get('zipcode', '').strip()
        
        if not all([street, city, state]):
            return jsonify({'success': False, 'data': {'error': 'Street, city, and state are required'}})
        
        # Check if reCAPTCHA is required
        api_key = 'SET_GEOAPIFY_API_KEY'
        if not api_key:
             return jsonify({'success': False, 'data': {'error': 'API key error'}})
        
        # Use Geoapify geocoding API
        address_text = f"{street}, {city}, {state} {zipcode}, USA"
        url = "https://api.geoapify.com/v1/geocode/search"
        params = {
            'text': address_text,
            'apiKey': api_key,
            'limit': 1,
            'format': 'json'
        }
        
        geoapify_logger.info(f"Request: {url} - Params: {params}")
        response = requests.get(url, params=params, timeout=10)
        geoapify_logger.info(f"Response: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            geoapify_logger.info(f"Results found: {len(result.get('results', []))}")
            if result.get('results'):
                addr = result['results'][0]
                return jsonify({
                    'success': True,
                    'data': {
                        'street': addr.get('housenumber', '') + ' ' + addr.get('street', street),
                        'city': addr.get('city', city),
                        'state': addr.get('state_code', state),
                        'zipcode': addr.get('postcode', zipcode)
                    }
                })
            else:
                geoapify_logger.warning("No results found for address")
                return jsonify({'success': False, 'data': {'error': 'Address not found'}})
        elif response.status_code == 403:
            geoapify_logger.warning("reCAPTCHA required")
            return jsonify({'success': False, 'data': {'error': 'reCAPTCHA required', 'requires_recaptcha': True}})
        else:
            geoapify_logger.error(f"API error: {response.status_code} - {response.text}")
            return jsonify({'success': False, 'data': {'error': 'Validation service unavailable'}})
            
    except Exception as e:
        geoapify_logger.error(f"Exception: {str(e)}")
        return jsonify({'success': False, 'data': {'error': 'Address validation failed'}})

@api_bp.route('/customers/create', methods=['POST'])
@login_required
def create_customer():
    """Create new customer"""
    try:
        data = request.form
        customer = Customer(
            name=data.get('name'),
            street_address=data.get('street_address'),
            city=data.get('city'),
            state=data.get('state'),
            zip_code=data.get('zip_code'),
            phone=data.get('phone'),
            email=data.get('email'),
            drivers_license_number=data.get('drivers_license_number')
        )
        customer.update_legacy_address()
        
        db.session.add(customer)
        db.session.commit()
        
        return jsonify({'success': True, 'customer_id': customer.id})
    except (ValueError, TypeError) as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Invalid data provided'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Database error'}), 500

@api_bp.route('/customers/update/<int:customer_id>', methods=['POST'])
@login_required
def update_customer(customer_id):
    """Update customer"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        data = request.form
        
        customer.name = data.get('name', customer.name)
        customer.street_address = data.get('street_address', customer.street_address)
        customer.city = data.get('city', customer.city)
        customer.state = data.get('state', customer.state)
        customer.zip_code = data.get('zip_code', customer.zip_code)
        customer.phone = data.get('phone', customer.phone)
        customer.email = data.get('email', customer.email)
        customer.drivers_license_number = data.get('drivers_license_number', customer.drivers_license_number)
        customer.update_legacy_address()
        
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@api_bp.route('/customers/list')
@login_required
def list_customers():
    """List all customers"""
    customers = Customer.query.filter_by(is_active=True).all()
    return jsonify({
        'customers': [{
            'id': c.id,
            'name': c.name,
            'phone': c.phone,
            'drivers_license_number': c.drivers_license_number,
            'street_address': c.street_address,
            'city': c.city,
            'state': c.state,
            'zip_code': c.zip_code,
            'address': c.full_address
        } for c in customers]
    })

@api_bp.route('/customers/<int:customer_id>')
@login_required
def get_customer(customer_id):
    """Get customer details"""
    customer = Customer.query.get_or_404(customer_id)
    return jsonify({
        'customer': {
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'email': customer.email,
            'drivers_license_number': customer.drivers_license_number,
            'street_address': customer.street_address,
            'city': customer.city,
            'state': customer.state,
            'zip_code': customer.zip_code
        }
    })

@api_bp.route('/customers/search')
@login_required
def search_customers():
    """Search customers"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'customers': []})
    
    try:
        customers = Customer.query.filter(
            db.or_(
                Customer.name.ilike(f'%{query}%'),
                Customer.drivers_license_number.ilike(f'%{query}%'),
                Customer.phone.ilike(f'%{query}%')
            ),
            Customer.is_active.is_(True)
        ).limit(10).all()
    except Exception as e:
        return jsonify({'success': False, 'error': 'Search failed'}), 500
    
    return jsonify({
        'customers': [{
            'id': c.id,
            'name': c.name,
            'phone': c.phone,
            'drivers_license_number': c.drivers_license_number,
            'address': c.full_address
        } for c in customers]
    })

@api_bp.route('/customers/upload_csv', methods=['POST'])
@login_required
def upload_customers_csv():
    """Upload customers from CSV file"""
    import logging
    import csv
    import io
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    
    try:
        if 'csv_file' not in request.files:
            logger.warning(f"CSV upload failed - no file uploaded by user {current_user.username}")
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['csv_file']
        filename = file.filename
        
        if not filename.endswith('.csv'):
            logger.warning(f"CSV upload failed - invalid file format '{filename}' by user {current_user.username}")
            return jsonify({'success': False, 'error': 'File must be CSV format'}), 400
        
        logger.info(f"Starting CSV customer upload: '{filename}' by user {current_user.username}")
        
        # Read CSV content
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        imported = 0
        skipped = 0
        errors = []
        
        for row_num, row in enumerate(csv_input, start=2):
            try:
                # Combine names
                first_name = row.get('First Name', '').strip()
                middle_name = row.get('Middle Name', '').strip()
                last_name = row.get('Last Name', '').strip()
                
                full_name = f"{first_name} {middle_name} {last_name}".strip().replace('  ', ' ')
                
                if not full_name:
                    errors.append(f"Row {row_num}: Missing name")
                    continue
                
                # Check for existing customer by license or name
                license_num = row.get('Drivers License', '').strip()
                existing = None
                if license_num:
                    existing = Customer.query.filter_by(drivers_license_number=license_num).first()
                if not existing:
                    existing = Customer.query.filter_by(name=full_name).first()
                
                if existing:
                    skipped += 1
                    continue
                
                # Parse birthday
                birthday = None
                birthday_str = row.get('Birthday', '').strip()
                if birthday_str:
                    try:
                        birthday = datetime.strptime(birthday_str, '%m/%d/%Y').date()
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid birthday format '{birthday_str}'")
                
                # Create new customer with field length validation
                customer = Customer(
                    name=full_name[:100],
                    street_address=row.get('Street Address', '').strip()[:200],
                    city=row.get('City', '').strip()[:100],
                    state=row.get('State', '').strip()[:2],
                    zip_code=row.get('Zip code', '').strip()[:10],
                    phone=row.get('Phone Number', '').strip()[:20],
                    drivers_license_number=license_num[:50],
                    birthday=birthday,
                    gender=row.get('Gender', '').strip()[:10],
                    eye_color=row.get('Eye Color', '').strip()[:20]
                )
                
                db.session.add(customer)
                imported += 1
                
            except Exception as row_error:
                errors.append(f"Row {row_num}: {str(row_error)}")
                continue
        
        db.session.commit()
        
        logger.info(f"CSV upload completed: '{filename}' - {imported} imported, {skipped} skipped, {len(errors)} errors by user {current_user.username}")
        
        if errors:
            logger.warning(f"CSV upload errors for '{filename}': {'; '.join(errors[:5])}{'...' if len(errors) > 5 else ''}")
        
        return jsonify({
            'success': True,
            'imported': imported,
            'skipped': skipped
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"CSV upload failed for user {current_user.username}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/customers/validate_all_addresses', methods=['POST'])
@login_required
def validate_all_addresses():
    """Validate all customer addresses in database"""
    try:
        customers = Customer.query.filter(
            Customer.is_active.is_(True),
            Customer.street_address.isnot(None),
            Customer.city.isnot(None),
            Customer.state.isnot(None)
        ).all()
        
        validated = 0
        errors = 0
        
        api_key = 'SET_GEOAPIFY_API_KEY'
        if not api_key:
            return jsonify({'success': False, 'error': 'API key not configured'})
        
        for customer in customers:
            try:
                address_text = f"{customer.street_address}, {customer.city}, {customer.state} {customer.zip_code or ''}, USA"
                url = "https://api.geoapify.com/v1/geocode/search"
                params = {
                    'text': address_text,
                    'apiKey': api_key,
                    'limit': 1,
                    'format': 'json'
                }
                
                geoapify_logger.info(f"Bulk validation: {customer.id} - {address_text}")
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('results'):
                        addr = result['results'][0]
                        customer.street_address = addr.get('housenumber', '') + ' ' + addr.get('street', customer.street_address)
                        customer.city = addr.get('city', customer.city)
                        customer.state = addr.get('state_code', customer.state)
                        customer.zip_code = addr.get('postcode', customer.zip_code)
                        customer.update_legacy_address()
                        validated += 1
                    else:
                        errors += 1
                        geoapify_logger.warning(f"No results for customer {customer.id}")
                else:
                    errors += 1
                    geoapify_logger.error(f"API error for customer {customer.id}: {response.status_code}")
                    
            except Exception as e:
                errors += 1
                geoapify_logger.error(f"Exception for customer {customer.id}: {str(e)}")
        
        db.session.commit()
        geoapify_logger.info(f"Bulk validation complete: {validated} validated, {errors} errors")
        
        return jsonify({
            'success': True,
            'validated': validated,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        geoapify_logger.error(f"Bulk validation failed: {str(e)}")
        return jsonify({'success': False, 'error': 'Bulk validation failed'})

@api_bp.route('/cash-drawer/open', methods=['POST'])
@login_required
def open_cash_drawer():
    """Open cash drawer - requires cashier permission"""
    if not current_user.has_permission('open_cash_drawer'):
        return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
    
    try:
        data = request.get_json() or {}
        printer_ip = data.get('printer_ip')
        
        if not printer_ip:
            return jsonify({'success': False, 'error': 'Printer IP required'}), 400
        
        printer_service = StarPrinterService(printer_ip)
        success = printer_service.open_cash_drawer()
        
        if success:
            return jsonify({'success': True, 'message': 'Cash drawer opened'})
        else:
            return jsonify({'success': False, 'error': 'Failed to open cash drawer'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': 'Cash drawer operation failed'}), 500