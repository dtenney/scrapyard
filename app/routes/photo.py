from flask import Blueprint, request, jsonify, send_file, abort
from flask_login import login_required
from app.models.customer import Customer
from app.services.photo_service import PhotoService
from app import db
import os
import logging

logger = logging.getLogger(__name__)

photo_bp = Blueprint('photo', __name__)

@photo_bp.route('/customer_photo/<int:customer_id>')
@login_required
def serve_customer_photo(customer_id):
    """Serve customer driver's license photo"""
    customer = Customer.query.get_or_404(customer_id)
    
    if not customer.drivers_license_photo_path:
        abort(404)
    
    photo_path = PhotoService.get_photo_path(customer.drivers_license_photo_path)
    
    if not photo_path or not os.path.exists(photo_path):
        abort(404)
    
    return send_file(photo_path)

@photo_bp.route('/upload_customer_photo/<int:customer_id>', methods=['POST'])
@login_required
def upload_customer_photo(customer_id):
    """Upload driver's license photo for customer"""
    customer = Customer.query.get_or_404(customer_id)
    
    if 'photo' not in request.files:
        return jsonify({'success': False, 'error': 'No photo file provided'}), 400
    
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    # Delete existing photo if present
    if customer.drivers_license_photo_path:
        PhotoService.delete_photo(customer.drivers_license_photo_path)
    
    # Save new photo
    relative_path, error = PhotoService.save_customer_photo(customer_id, file)
    
    if error:
        from markupsafe import escape
        return jsonify({'success': False, 'error': escape(error)}), 400
    
    # Update customer record
    customer.drivers_license_photo_path = relative_path
    customer.drivers_license_photo_filename = file.filename
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'photo_url': f'/customer_photo/{customer_id}'
    })