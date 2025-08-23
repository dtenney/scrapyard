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
    
    # Create logo directory
    logo_dir = '/var/www/scrapyard/static/receipt_logos'
    os.makedirs(logo_dir, exist_ok=True)
    
    # Generate secure filename
    filename = f"logo_{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(logo_dir, filename)
    
    file.save(filepath)
    template.header_logo_path = filename
    db.session.commit()
    
    return jsonify({'success': True, 'filename': filename})

@receipt_templates_bp.route('/delete/<int:template_id>', methods=['POST'])
def delete(template_id):
    template = ReceiptTemplate.query.get_or_404(template_id)
    
    # Don't delete if it's the default template
    if template.is_default:
        return jsonify({'success': False, 'error': 'Cannot delete default template'})
    
    template.is_active = False
    db.session.commit()
    
    return jsonify({'success': True})