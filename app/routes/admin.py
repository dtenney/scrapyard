from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.user import User, UserGroup
from app.models.device import Device
from app import db

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@login_required
def require_admin():
    if not current_user.is_admin:
        return redirect(url_for('main.index'))

@admin_bp.route('/')
def index():
    return render_template('admin/dashboard.html')

@admin_bp.route('/users')
def users():
    users = User.query.all()
    groups = UserGroup.query.all()
    return render_template('admin/users.html', users=users, groups=groups)

@admin_bp.route('/users/create', methods=['POST'])
def create_user():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    
    user = User(username=username, email=email)
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    flash('User created successfully')
    return redirect(url_for('admin.users'))

@admin_bp.route('/devices')
def devices():
    devices = Device.query.all()
    return render_template('admin/devices.html', devices=devices)

@admin_bp.route('/devices/create', methods=['POST'])
def create_device():
    data = request.get_json()
    
    device = Device(
        name=data['name'],
        device_type=data['device_type'],
        ip_address=data['ip_address'],
        port=data.get('port'),
        model=data.get('model'),
        config=data.get('config', {})
    )
    
    db.session.add(device)
    db.session.commit()
    
    return jsonify({'success': True, 'device_id': device.id})

@admin_bp.route('/groups')
def groups():
    groups = UserGroup.query.all()
    return render_template('admin/groups.html', groups=groups)