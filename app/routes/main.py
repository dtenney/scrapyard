from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    """Main dashboard with touch-screen interface"""
    return render_template('dashboard.html', user=current_user)

@main_bp.route('/transaction')
@login_required
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