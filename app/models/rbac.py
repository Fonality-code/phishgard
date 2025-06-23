"""
Role-Based Access Control (RBAC) models
"""
from datetime import datetime
from app.extensions import db
from typing import List


# Association tables for many-to-many relationships
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)


class Role(db.Model):
    """Role model for RBAC"""
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    is_system = db.Column(db.Boolean, default=False)  # System roles cannot be deleted
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Many-to-many relationship with permissions
    permissions = db.relationship('Permission',
                                secondary=role_permissions,
                                back_populates='roles',
                                lazy='dynamic')

    def __repr__(self):
        return f'<Role {self.name}>'

    def has_permission(self, permission_name: str) -> bool:
        """Check if role has a specific permission"""
        return self.permissions.filter_by(name=permission_name).first() is not None

    def add_permission(self, permission):
        """Add permission to role"""
        if not self.has_permission(permission.name):
            self.permissions.append(permission)

    def remove_permission(self, permission):
        """Remove permission from role"""
        if self.has_permission(permission.name):
            self.permissions.remove(permission)


class Permission(db.Model):
    """Permission model for RBAC"""
    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    resource = db.Column(db.String(64), nullable=False)  # e.g., 'user', 'order', 'product'
    action = db.Column(db.String(32), nullable=False)    # e.g., 'create', 'read', 'update', 'delete'
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Many-to-many relationship with roles
    roles = db.relationship('Role',
                          secondary=role_permissions,
                          back_populates='permissions',
                          lazy='dynamic')

    def __repr__(self):
        return f'<Permission {self.name}>'


class UserRelationship(db.Model):
    """Model for managing relationships between users (e.g., manager-employee, parent company-subsidiary)"""
    __tablename__ = 'user_relationships'

    id = db.Column(db.Integer, primary_key=True)
    parent_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    child_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    relationship_type = db.Column(db.String(32), nullable=False)  # 'manager', 'parent_company', 'team_lead', etc.
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    parent_user = db.relationship('User', foreign_keys=[parent_user_id], backref='subordinates')
    child_user = db.relationship('User', foreign_keys=[child_user_id], backref='supervisors')
    creator = db.relationship('User', foreign_keys=[created_by])

    __table_args__ = (
        db.UniqueConstraint('parent_user_id', 'child_user_id', 'relationship_type',
                          name='unique_relationship'),
    )

    def __repr__(self):
        return f'<UserRelationship {self.parent_user_id}->{self.child_user_id} ({self.relationship_type})>'


class AccessControl(db.Model):
    """Model for fine-grained access control based on relationships"""
    __tablename__ = 'access_controls'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resource_type = db.Column(db.String(64), nullable=False)  # 'user', 'order', 'product', etc.
    resource_id = db.Column(db.Integer, nullable=True)  # Specific resource ID, NULL for all resources of type
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), nullable=False)
    granted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    relationship_required = db.Column(db.String(32), nullable=True)  # Required relationship type
    is_granted = db.Column(db.Boolean, default=True)  # True for grant, False for explicit deny
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='access_controls')
    permission = db.relationship('Permission')
    granter = db.relationship('User', foreign_keys=[granted_by])

    def __repr__(self):
        action = "GRANT" if self.is_granted else "DENY"
        return f'<AccessControl {action} {self.user_id} -> {self.resource_type}:{self.resource_id}>'

    @property
    def is_expired(self):
        """Check if access control entry has expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
