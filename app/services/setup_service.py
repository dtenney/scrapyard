from app import db
from app.models.user import UserGroup
from app.models.permissions import Permission, GroupPermission, DEFAULT_PERMISSIONS, DEFAULT_GROUPS

def initialize_default_groups():
    """Initialize default permissions and groups"""
    
    # Create default permissions
    for perm_name, perm_desc in DEFAULT_PERMISSIONS:
        if not Permission.query.filter_by(name=perm_name).first():
            permission = Permission(name=perm_name, description=perm_desc)
            db.session.add(permission)
    
    db.session.commit()
    
    # Create default groups
    for group_name, group_config in DEFAULT_GROUPS.items():
        if not UserGroup.query.filter_by(name=group_name).first():
            group = UserGroup(
                name=group_name,
                description=group_config['description']
            )
            db.session.add(group)
            db.session.commit()
            
            # Add permissions to group
            for perm_name in group_config['permissions']:
                permission = Permission.query.filter_by(name=perm_name).first()
                if permission:
                    group_perm = GroupPermission(
                        group_id=group.id,
                        permission_id=permission.id
                    )
                    db.session.add(group_perm)
    
    db.session.commit()
    print("Default groups and permissions initialized")