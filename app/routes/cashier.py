from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db

cashier_bp = Blueprint('cashier', __name__)

def require_permission(permission):
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if not current_user.has_permission(permission):
                return jsonify({'error': 'Permission denied'}), 403
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

@cashier_bp.route('/dashboard')
@login_required
@require_permission('transaction')
def dashboard():
    """Cashier point of sale dashboard"""
    from app.models.material import Material
    materials = Material.query.filter_by(is_active=True).order_by(Material.category, Material.description).all()
    return render_template('cashier_dashboard.html', materials=materials)

@cashier_bp.route('/api/scale/weight')
@login_required
@require_permission('transaction')
def get_scale_weight():
    """Get current scale weight"""
    from app.models.device import Device
    from app.services.scale_service import USRScaleService
    
    scale = Device.query.filter_by(device_type='scale', is_active=True).first()
    if not scale:
        return jsonify({'weight': 0.0, 'stable': False})
    
    try:
        service = USRScaleService(scale.ip_address, scale.serial_port)
        weight_data = service.get_weight()
        return jsonify(weight_data)
    except:
        return jsonify({'weight': 0.0, 'stable': False})

@cashier_bp.route('/api/scale/tare', methods=['POST'])
@login_required
@require_permission('transaction')
def tare_scale():
    """Tare the scale"""
    from app.models.device import Device
    from app.services.scale_service import USRScaleService
    
    scale = Device.query.filter_by(device_type='scale', is_active=True).first()
    if not scale:
        return jsonify({'success': False, 'error': 'No scale available'})
    
    try:
        service = USRScaleService(scale.ip_address, scale.serial_port)
        result = service.tare_scale()
        return jsonify({'success': result})
    except:
        return jsonify({'success': False})



@cashier_bp.route('/api/transactions/create', methods=['POST'])
@login_required
@require_permission('transaction')
def create_transaction():
    """Create new transaction"""
    from app.models.transaction import Transaction, TransactionItem
    
    try:
        data = request.get_json()
        
        transaction = Transaction(
            customer_id=data['customerId'],
            total_amount=data['total'],
            cashier_id=current_user.id
        )
        
        db.session.add(transaction)
        db.session.flush()
        
        for item_data in data['items']:
            item = TransactionItem(
                transaction_id=transaction.id,
                material_id=item_data['materialId'],
                weight_pounds=item_data['weight'],
                price_per_pound=item_data['pricePerLb'],
                total_value=item_data['total']
            )
            db.session.add(item)
        
        db.session.commit()
        
        return jsonify({'success': True, 'transaction_id': transaction.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Transaction failed'}), 500