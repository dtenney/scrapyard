from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.customer import Customer
from app.services.smarty_service import SmartyAddressService

api_bp = Blueprint('api', __name__)
smarty_service = SmartyAddressService()

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
    """Validate address using Smarty Streets"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid JSON data'}), 400
            
        street = data.get('street', '').strip()
        city = data.get('city', '').strip()
        state = data.get('state', '').strip()
        zipcode = data.get('zipcode', '').strip()
        
        if not all([street, city, state, zipcode]):
            return jsonify({'success': False, 'error': 'All address fields required'})
        
        is_valid, result = smarty_service.validate_address(street, city, state, zipcode)
        return jsonify({'success': is_valid, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': 'Validation failed'}), 500

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