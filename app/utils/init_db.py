"""
Database initialization script for RBAC
"""
from app.extensions import db
from app.models import Role, Permission, User


def init_rbac():
    """Initialize default roles and permissions"""

    # Create basic permissions
    permissions_data = [
        # User permissions
        ('user.create', 'Create users', 'user', 'create'),
        ('user.read', 'Read user information', 'user', 'read'),
        ('user.update', 'Update user information', 'user', 'update'),
        ('user.delete', 'Delete users', 'user', 'delete'),
        ('user.list', 'List users', 'user', 'list'),

        # Role permissions
        ('role.create', 'Create roles', 'role', 'create'),
        ('role.read', 'Read role information', 'role', 'read'),
        ('role.update', 'Update role information', 'role', 'update'),
        ('role.delete', 'Delete roles', 'role', 'delete'),
        ('role.assign', 'Assign roles to users', 'role', 'assign'),

        # Permission permissions
        ('permission.create', 'Create permissions', 'permission', 'create'),
        ('permission.read', 'Read permission information', 'permission', 'read'),
        ('permission.update', 'Update permission information', 'permission', 'update'),
        ('permission.delete', 'Delete permissions', 'permission', 'delete'),
        ('permission.assign', 'Assign permissions to roles', 'permission', 'assign'),

        # Relationship permissions
        ('relationship.create', 'Create user relationships', 'relationship', 'create'),
        ('relationship.read', 'Read user relationships', 'relationship', 'read'),
        ('relationship.update', 'Update user relationships', 'relationship', 'update'),
        ('relationship.delete', 'Delete user relationships', 'relationship', 'delete'),

        # Access control permissions
        ('access.grant', 'Grant access to resources', 'access', 'grant'),
        ('access.revoke', 'Revoke access to resources', 'access', 'revoke'),
        ('access.read', 'Read access control information', 'access', 'read'),

        # System permissions
        ('system.admin', 'Full system administration', 'system', 'admin'),
        ('system.monitor', 'Monitor system status', 'system', 'monitor'),
    ]

    created_permissions = {}
    for name, description, resource, action in permissions_data:
        permission = Permission.query.filter_by(name=name).first()
        if not permission:
            permission = Permission(
                name=name,
                description=description,
                resource=resource,
                action=action
            )
            db.session.add(permission)
            print(f"Created permission: {name}")
        created_permissions[name] = permission

    # Create basic roles
    roles_data = [
        ('admin', 'System Administrator', True, [
            'system.admin', 'user.create', 'user.read', 'user.update', 'user.delete', 'user.list',
            'role.create', 'role.read', 'role.update', 'role.delete', 'role.assign',
            'permission.create', 'permission.read', 'permission.update', 'permission.delete', 'permission.assign',
            'relationship.create', 'relationship.read', 'relationship.update', 'relationship.delete',
            'access.grant', 'access.revoke', 'access.read', 'system.monitor'
        ]),
        ('manager', 'Manager', True, [
            'user.read', 'user.update', 'user.list',
            'relationship.create', 'relationship.read', 'relationship.update',
            'access.read', 'system.monitor'
        ]),
        ('user', 'Regular User', True, [
            'user.read'  # Users can read their own information
        ]),
        ('customer', 'Customer', True, [
            'user.read'
        ]),
        ('business', 'Business User', True, [
            'user.read', 'user.update'
        ])
    ]

    for name, description, is_system, permission_names in roles_data:
        role = Role.query.filter_by(name=name).first()
        if not role:
            role = Role(
                name=name,
                description=description,
                is_system=is_system
            )
            db.session.add(role)
            print(f"Created role: {name}")

        # Assign permissions to role
        for permission_name in permission_names:
            if permission_name in created_permissions:
                role.add_permission(created_permissions[permission_name])

    # Commit all changes
    try:
        db.session.commit()
        print("RBAC initialization completed successfully!")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing RBAC: {e}")
        return False


def create_admin_user(email, password, first_name, last_name):
    """Create an admin user"""

    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        print(f"User with email {email} already exists")
        return existing_user

    # Create admin user
    admin_user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        country='US',
        city='Admin City',
        preferred_language='en',
        account_type='customer',
        account_status='active',
        email_verified=True
    )
    admin_user.set_password(password)

    # Add user to session and commit first
    db.session.add(admin_user)
    db.session.commit()

    # Now add admin role using direct relationship
    admin_role = Role.query.filter_by(name='admin').first()
    if admin_role:
        admin_user.roles.append(admin_role)
        db.session.commit()

    print(f"Admin user created: {email}")
    return admin_user


def assign_default_roles():
    """Assign default roles to existing users based on account type"""

    users = User.query.all()
    user_role = Role.query.filter_by(name='user').first()
    customer_role = Role.query.filter_by(name='customer').first()
    business_role = Role.query.filter_by(name='business').first()

    for user in users:
        # Skip if user already has roles
        if len(list(user.roles)) > 0:
            continue

        # Assign roles based on account type
        if user.account_type == 'customer':
            if customer_role:
                user.roles.append(customer_role)
        elif user.account_type == 'business':
            if business_role:
                user.roles.append(business_role)
        elif user.account_type == 'both':
            if customer_role:
                user.roles.append(customer_role)
            if business_role:
                user.roles.append(business_role)

        # Always add the basic user role
        if user_role:
            user.roles.append(user_role)

    try:
        db.session.commit()
        print("Default roles assigned to existing users")
    except Exception as e:
        db.session.rollback()
        print(f"Error assigning default roles: {e}")


if __name__ == '__main__':
    from app import create_app

    app = create_app()
    with app.app_context():
        # Initialize database tables
        db.create_all()

        # Initialize RBAC
        init_rbac()

        # Create admin user
        create_admin_user(
            email='admin@example.com',
            password='admin123',
            first_name='Admin',
            last_name='User'
        )

        # Assign default roles
        assign_default_roles()

        print("Database initialization completed!")
