"""
RBAC Management utilities
"""
from app.extensions import db
from app.models import User, Role, Permission, UserRelationship, AccessControl
from typing import List, Optional


class RBACManager:
    """Class to manage RBAC operations"""

    @staticmethod
    def create_role(name: str, description: str = None, is_system: bool = False) -> Role:
        """Create a new role"""
        role = Role(name=name, description=description, is_system=is_system)
        db.session.add(role)
        db.session.commit()
        return role

    @staticmethod
    def create_permission(name: str, description: str, resource: str, action: str) -> Permission:
        """Create a new permission"""
        permission = Permission(
            name=name,
            description=description,
            resource=resource,
            action=action
        )
        db.session.add(permission)
        db.session.commit()
        return permission

    @staticmethod
    def assign_role_to_user(user: User, role: Role) -> bool:
        """Assign a role to a user"""
        try:
            user.add_role(role)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error assigning role {role.name} to user {user.email}: {e}")
            return False

    @staticmethod
    def remove_role_from_user(user: User, role: Role) -> bool:
        """Remove a role from a user"""
        try:
            user.remove_role(role)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error removing role {role.name} from user {user.email}: {e}")
            return False

    @staticmethod
    def assign_permission_to_role(role: Role, permission: Permission) -> bool:
        """Assign a permission to a role"""
        try:
            role.add_permission(permission)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error assigning permission {permission.name} to role {role.name}: {e}")
            return False

    @staticmethod
    def create_user_relationship(parent_user: User, child_user: User,
                               relationship_type: str, created_by: User) -> UserRelationship:
        """Create a relationship between two users"""
        relationship = UserRelationship(
            parent_user_id=parent_user.id,
            child_user_id=child_user.id,
            relationship_type=relationship_type,
            created_by=created_by.id
        )
        db.session.add(relationship)
        db.session.commit()
        return relationship

    @staticmethod
    def grant_access(user: User, permission: Permission, resource_type: str,
                    resource_id: Optional[int], granted_by: User,
                    relationship_required: Optional[str] = None,
                    expires_at=None) -> AccessControl:
        """Grant specific access to a user"""
        access_control = AccessControl(
            user_id=user.id,
            resource_type=resource_type,
            resource_id=resource_id,
            permission_id=permission.id,
            granted_by=granted_by.id,
            relationship_required=relationship_required,
            is_granted=True,
            expires_at=expires_at
        )
        db.session.add(access_control)
        db.session.commit()
        return access_control

    @staticmethod
    def revoke_access(user: User, permission: Permission, resource_type: str,
                     resource_id: Optional[int], granted_by: User) -> AccessControl:
        """Revoke specific access from a user"""
        access_control = AccessControl(
            user_id=user.id,
            resource_type=resource_type,
            resource_id=resource_id,
            permission_id=permission.id,
            granted_by=granted_by.id,
            is_granted=False
        )
        db.session.add(access_control)
        db.session.commit()
        return access_control

    @staticmethod
    def check_user_permission(user: User, permission_name: str,
                            resource_type: str = None, resource_id: int = None) -> bool:
        """Check if a user has a specific permission"""
        return user.has_permission(permission_name, resource_type, resource_id)

    @staticmethod
    def get_user_accessible_resources(user: User, resource_type: str) -> List[int]:
        """Get list of resource IDs that a user can access"""
        if resource_type == 'user':
            return user.get_accessible_users()

        # For other resource types, implement similar logic
        # This is a placeholder that would need to be expanded
        return []

    @staticmethod
    def list_user_roles(user: User) -> List[Role]:
        """Get all roles assigned to a user"""
        return list(user.roles)

    @staticmethod
    def list_role_permissions(role: Role) -> List[Permission]:
        """Get all permissions assigned to a role"""
        return list(role.permissions)

    @staticmethod
    def list_user_relationships(user: User, as_parent: bool = True) -> List[UserRelationship]:
        """Get user relationships where user is parent or child"""
        if as_parent:
            return UserRelationship.query.filter_by(
                parent_user_id=user.id,
                is_active=True
            ).all()
        else:
            return UserRelationship.query.filter_by(
                child_user_id=user.id,
                is_active=True
            ).all()


def require_permission(permission_name: str, resource_type: str = None):
    """Decorator to require specific permission for a view"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            from flask_login import current_user
            from flask import flash, redirect, url_for

            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login'))

            resource_id = kwargs.get('id') or kwargs.get('user_id') or kwargs.get('resource_id')

            if not current_user.has_permission(permission_name, resource_type, resource_id):
                flash('Access denied. Insufficient permissions.', 'error')
                return redirect(url_for('main.index'))

            return f(*args, **kwargs)

        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator


def require_role(role_name: str):
    """Decorator to require specific role for a view"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            from flask_login import current_user
            from flask import flash, redirect, url_for

            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login'))

            if not current_user.has_role(role_name):
                flash(f'Access denied. {role_name.title()} role required.', 'error')
                return redirect(url_for('main.index'))

            return f(*args, **kwargs)

        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator
