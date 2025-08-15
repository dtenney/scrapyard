from app import db
from datetime import datetime

class Permission(db.Model):
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

class GroupPermission(db.Model):
    __tablename__ = 'group_permissions'
    
    group_id = db.Column(db.Integer, db.ForeignKey('user_groups.id'), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), primary_key=True)

# Default permissions
DEFAULT_PERMISSIONS = [
    ('transaction', 'Access transaction processing'),
    ('customer_lookup', 'Access customer lookup'),
    ('reports', 'Access reports and analytics'),
    ('admin', 'Administrative access')
]

# Default groups with permissions
DEFAULT_GROUPS = {
    'mechanics': {
        'description': 'Mechanics - Transaction entry only',
        'permissions': ['transaction']
    },
    'cashier': {
        'description': 'Cashier - Full POS access',
        'permissions': ['transaction', 'customer_lookup', 'reports']
    },
    'reporter': {
        'description': 'Reporter - Customer and reports access',
        'permissions': ['customer_lookup', 'reports']
    }
}