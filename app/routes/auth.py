from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET'])
def login_get():
    """Display login form"""
    from app.models.user import User
    
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # Check if admin user exists
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        return redirect(url_for('auth.setup'))
    
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login_post():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """First-time admin setup"""
    # Check if admin user already exists
    admin_user = User.query.filter_by(username='admin').first()
    if admin_user:
        return redirect(url_for('auth.login_get'))
    
    if request.method == 'POST':
        username = request.form.get('username', 'admin')
        password = request.form['password']
        email = request.form['email']
        
        try:
            admin_user = User(username=username, email=email, is_admin=True)
            admin_user.set_password(password)
            
            db.session.add(admin_user)
            db.session.commit()
            
            flash('Admin account created successfully!')
            return redirect(url_for('auth.login_get'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating admin account')
    
    return render_template('setup.html')