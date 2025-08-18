from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    groups = db.relationship('UserGroup', secondary='user_group_members', back_populates='users')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission_name):
        if self.is_admin:
            return True
        
        from app.models.permissions import Permission, GroupPermission
        
        # Single query to check permission across all user groups
        group_ids = [group.id for group in self.groups]
        if not group_ids:
            return False
            
        permission_exists = db.session.query(Permission).join(GroupPermission).filter(
            GroupPermission.group_id.in_(group_ids),
            Permission.name == permission_name
        ).first()
        
        return permission_exists is not None

class UserGroup(db.Model):
    __tablename__ = 'user_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', secondary='user_group_members', back_populates='groups')

class UserGroupMember(db.Model):
    __tablename__ = 'user_group_members'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('user_groups.id'), primary_key=True)