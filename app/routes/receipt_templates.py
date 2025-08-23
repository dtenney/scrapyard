from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models.receipt_template import ReceiptTemplate
from app import db
import os
import uuid
from werkzeug.utils import secure_filename

receipt_templates_bp = Blueprint('receipt_templates', __name__)

@receipt_templates_bp.before_request
@login_required
def require_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for('main.index'))

@receipt_templates_bp.route('/')
def index():
    templates = ReceiptTemplate.query.filter_by(is_active=True).all()
    return render_template('admin/receipt_templates.html', templates=templates)

@receipt_templates_bp.route('/create', methods=['POST'])
def create():
    data = request.get_json()
    
    template = ReceiptTemplate(
        name=data['name'],
        company_name=data.get('company_name', ''),
        company_address=data.get('company_address', ''),
        footer_text=data.get('footer_text', ''),
        is_default=data.get('is_default', False)
    )
    
    # If this is set as default, unset others
    if template.is_default:
        ReceiptTemplate.query.filter_by(is_default=True).update({'is_default': False})
    
    db.session.add(template)
    db.session.commit()
    
    return jsonify({'success': True, 'template_id': template.id})

@receipt_templates_bp.route('/<int:template_id>')
def get_template(template_id):
    template = ReceiptTemplate.query.get_or_404(template_id)
    return jsonify({
        'template': {
            'id': template.id,
            'name': template.name,
            'company_name': template.company_name,
            'company_address': template.company_address,
            'footer_text': template.footer_text,
            'header_logo_path': template.header_logo_path,
            'is_default': template.is_default
        }
    })

@receipt_templates_bp.route('/update/<int:template_id>', methods=['POST'])
def update(template_id):
    template = ReceiptTemplate.query.get_or_404(template_id)
    data = request.get_json()
    
    template.name = data['name']
    template.company_name = data.get('company_name', '')
    template.company_address = data.get('company_address', '')
    template.footer_text = data.get('footer_text', '')
    template.is_default = data.get('is_default', False)
    
    # If this is set as default, unset others
    if template.is_default:
        ReceiptTemplate.query.filter(ReceiptTemplate.id != template_id, ReceiptTemplate.is_default == True).update({'is_default': False})
    
    db.session.commit()
    return jsonify({'success': True})

@receipt_templates_bp.route('/upload_logo/<int:template_id>', methods=['POST'])
def upload_logo(template_id):
    template = ReceiptTemplate.query.get_or_404(template_id)
    
    if 'logo' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['logo']
    if not file.filename:
        return jsonify({'success': False, 'error': 'No file selected'})
    
    # Validate file type
    if not file.filename.lower().endswith(('.jpg', '.jpeg')):
        return jsonify({'success': False, 'error': 'Only JPG files allowed'})
    
    try:
        # Create logo directory
        logo_dir = '/var/www/scrapyard/app/static/receipt_logos'
        os.makedirs(logo_dir, exist_ok=True)
        
        # Generate secure filename
        filename = f"logo_{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(logo_dir, filename)
        
        file.save(filepath)
        template.header_logo_path = filename
        db.session.commit()
        
        return jsonify({'success': True, 'filename': filename})
    except PermissionError:
        return jsonify({'success': False, 'error': 'Permission denied - check directory permissions'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@receipt_templates_bp.route('/preview/<int:template_id>')
def preview(template_id):
    template = ReceiptTemplate.query.get_or_404(template_id)
    
    # Sample transaction data for preview
    sample_data = {
        'customer_name': 'John Smith',
        'transaction_date': '2025-08-23 18:30:00',
        'transaction_id': 'TXN-001234',
        'items': [
            {'description': '#1 Copper', 'weight': 25.50, 'price_per_lb': 3.25, 'total': 82.88},
            {'description': 'Aluminum Cans', 'weight': 12.75, 'price_per_lb': 0.85, 'total': 10.84},
            {'description': 'Steel Scrap', 'weight': 150.00, 'price_per_lb': 0.12, 'total': 18.00}
        ],
        'subtotal': 111.72,
        'total': 111.72
    }
    
    return render_template('admin/receipt_preview.html', template=template, data=sample_data)

@receipt_templates_bp.route('/delete/<int:template_id>', methods=['POST'])
def delete(template_id):
    template = ReceiptTemplate.query.get_or_404(template_id)
    
    # Don't delete if it's the default template
    if template.is_default:
        return jsonify({'success': False, 'error': 'Cannot delete default template'})
    
    template.is_active = False
    db.session.commit()
    
    return jsonify({'success': True})