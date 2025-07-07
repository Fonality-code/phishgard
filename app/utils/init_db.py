"""
Database initialization script for RBAC
"""
from app.extensions import db
from app.models import Role, Permission, User
from app.models.simulation import EmailTemplate


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


def create_default_email_templates():
    """Create default email templates available to all users"""

    # Get the admin user to assign as creator
    admin_user = User.query.filter_by(email='admin@example.com').first()
    if not admin_user:
        admin_user = User.query.filter(User.roles.any(name='admin')).first()

    if not admin_user:
        print("No admin user found. Cannot create default templates.")
        return False

    default_templates = [
        {
            'name': 'Urgent Security Alert',
            'description': 'A high-priority security alert template that creates urgency and prompts immediate action.',
            'category': 'security_alert',
            'difficulty_level': 'medium',
            'subject': 'URGENT: Security Breach Detected - Immediate Action Required',
            'sender_name': 'IT Security Team',
            'sender_email': 'security@company.com',
            'html_content': '''
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
    <div style="background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%); color: white; padding: 20px; text-align: center;">
        <h1 style="margin: 0; font-size: 24px; font-weight: bold;">🔒 SECURITY ALERT</h1>
        <p style="margin: 5px 0 0 0; font-size: 14px;">Immediate attention required</p>
    </div>
    <div style="padding: 30px 20px; background-color: #f8fafc;">
        <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 15px; margin-bottom: 20px;">
            <p style="margin: 0; color: #b91c1c; font-weight: bold;">⚠️ CRITICAL SECURITY BREACH DETECTED</p>
        </div>

        <p style="color: #374151; margin-bottom: 15px;">Dear {{employee.first_name}},</p>

        <p style="color: #374151; margin-bottom: 15px;">
            Our security systems have detected unauthorized access attempts on your account ({{employee.email}})
            from an unrecognized location. Your account has been temporarily locked for protection.
        </p>

        <p style="color: #374151; margin-bottom: 20px;">
            <strong>Immediate action is required to prevent data loss and restore access.</strong>
        </p>

        <div style="background-color: #ffffff; border: 1px solid #e5e7eb; padding: 15px; margin: 20px 0;">
            <p style="margin: 0 0 10px 0; font-size: 14px; color: #6b7280;">Suspicious Activity Details:</p>
            <ul style="color: #374151; margin: 0; padding-left: 20px;">
                <li>Time: Today, 3:47 AM</li>
                <li>Location: Unknown (VPN detected)</li>
                <li>Device: Unrecognized</li>
            </ul>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{tracking_url}}" style="background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block; font-size: 16px;">
                🔐 SECURE MY ACCOUNT NOW
            </a>
        </div>

        <p style="color: #374151; font-size: 14px; margin-bottom: 20px;">
            <strong>Important:</strong> You have 24 hours to verify your account before it will be permanently disabled.
        </p>

        <div style="background-color: #fffbeb; border: 1px solid #fbbf24; padding: 15px; margin: 20px 0;">
            <p style="margin: 0; color: #92400e; font-size: 14px;">
                If you do not recognize this activity, please contact IT immediately at security@company.com
            </p>
        </div>

        <p style="color: #374151; margin-bottom: 5px;">Best regards,</p>
        <p style="color: #374151; margin: 0; font-weight: bold;">IT Security Team</p>
    </div>
    <div style="background-color: #1e3a8a; color: white; padding: 15px; text-align: center; font-size: 12px;">
        This is an automated security notification. Do not reply to this email.
    </div>
</div>
            ''',
            'landing_page_content': 'This was a phishing simulation. In a real attack, clicking this link could have compromised your credentials.'
        },

        {
            'name': 'Password Expiry Notification',
            'description': 'A professional password expiry notice that prompts users to update their credentials.',
            'category': 'it_support',
            'difficulty_level': 'easy',
            'subject': 'Password Expiry Notice - Update Required Within 3 Days',
            'sender_name': 'IT Help Desk',
            'sender_email': 'helpdesk@company.com',
            'html_content': '''
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
    <div style="background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%); color: white; padding: 20px; text-align: center;">
        <h1 style="margin: 0; font-size: 22px; font-weight: bold;">🔑 Password Update Required</h1>
        <p style="margin: 5px 0 0 0; font-size: 14px;">Your password will expire soon</p>
    </div>
    <div style="padding: 30px 20px;">
        <p style="color: #374151; margin-bottom: 15px;">Hello {{employee.first_name}},</p>

        <p style="color: #374151; margin-bottom: 15px;">
            This is a friendly reminder that your password for {{employee.email}} will expire in <strong>3 days</strong>.
        </p>

        <p style="color: #374151; margin-bottom: 20px;">
            To avoid any interruption to your work, please update your password now using the secure link below.
        </p>

        <div style="background-color: #f0f4ff; border: 1px solid #c7d2fe; padding: 15px; margin: 20px 0;">
            <p style="margin: 0 0 10px 0; font-weight: bold; color: #1e3a8a;">Password Requirements:</p>
            <ul style="color: #374151; margin: 0; padding-left: 20px; font-size: 14px;">
                <li>At least 8 characters long</li>
                <li>Include uppercase and lowercase letters</li>
                <li>Include at least one number</li>
                <li>Include at least one special character</li>
            </ul>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{tracking_url}}" style="background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%); color: white; padding: 12px 25px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                Update Password Now
            </a>
        </div>

        <p style="color: #374151; font-size: 14px; margin-bottom: 20px;">
            For security reasons, this link will expire in 24 hours.
        </p>

        <p style="color: #374151; margin-bottom: 5px;">If you have any questions, please contact our help desk.</p>
        <p style="color: #374151; margin-bottom: 5px;">Best regards,</p>
        <p style="color: #374151; margin: 0; font-weight: bold;">IT Help Desk</p>
    </div>
    <div style="background-color: #f8fafc; padding: 15px; text-align: center; font-size: 12px; color: #6b7280;">
        Company IT Department | Help Desk: support@company.com
    </div>
</div>
            ''',
            'landing_page_content': 'This was a phishing simulation testing password update awareness.'
        },

        {
            'name': 'Fake Invoice Payment Request',
            'description': 'A business email compromise template simulating an urgent invoice payment request.',
            'category': 'finance',
            'difficulty_level': 'hard',
            'subject': 'URGENT: Outstanding Invoice #INV-2024-0847 - Payment Required',
            'sender_name': 'Accounts Receivable',
            'sender_email': 'billing@company-suppliers.com',
            'html_content': '''
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
    <div style="background-color: #ffffff; border-bottom: 3px solid #1e3a8a; padding: 20px;">
        <div style="display: flex; align-items: center;">
            <div style="background-color: #1e3a8a; color: white; padding: 10px; border-radius: 4px; margin-right: 15px;">
                <strong>INVOICE</strong>
            </div>
            <div>
                <h1 style="margin: 0; color: #1e3a8a; font-size: 20px;">Payment Reminder</h1>
                <p style="margin: 5px 0 0 0; color: #6b7280; font-size: 14px;">Invoice #INV-2024-0847</p>
            </div>
        </div>
    </div>
    <div style="padding: 30px 20px;">
        <p style="color: #374151; margin-bottom: 15px;">Dear {{employee.first_name}},</p>

        <p style="color: #374151; margin-bottom: 15px;">
            We hope this email finds you well. We are writing to follow up on the outstanding invoice below:
        </p>

        <div style="background-color: #f8fafc; border: 1px solid #e5e7eb; padding: 20px; margin: 20px 0;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; color: #374151;">Invoice Number:</td>
                    <td style="padding: 8px 0; color: #374151;">INV-2024-0847</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; color: #374151;">Invoice Date:</td>
                    <td style="padding: 8px 0; color: #374151;">December 15, 2024</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; color: #374151;">Due Date:</td>
                    <td style="padding: 8px 0; color: #ef4444; font-weight: bold;">January 14, 2025 (OVERDUE)</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; color: #374151;">Amount Due:</td>
                    <td style="padding: 8px 0; color: #374151; font-size: 18px; font-weight: bold;">$4,750.00</td>
                </tr>
            </table>
        </div>

        <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0;">
            <p style="margin: 0; color: #b91c1c;">
                <strong>URGENT:</strong> This invoice is now 23 days overdue. Immediate payment is required to avoid service disruption.
            </p>
        </div>

        <p style="color: #374151; margin-bottom: 20px;">
            Please process the payment at your earliest convenience. You can view and pay the invoice securely using the link below:
        </p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{tracking_url}}" style="background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%); color: white; padding: 12px 25px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                View Invoice & Pay Online
            </a>
        </div>

        <p style="color: #374151; font-size: 14px; margin-bottom: 20px;">
            If you have already processed this payment, please disregard this notice. For any questions regarding this invoice, please contact our billing department.
        </p>

        <p style="color: #374151; margin-bottom: 5px;">Thank you for your prompt attention to this matter.</p>
        <p style="color: #374151; margin-bottom: 5px;">Best regards,</p>
        <p style="color: #374151; margin: 0; font-weight: bold;">Accounts Receivable Department</p>
    </div>
    <div style="background-color: #f8fafc; padding: 15px; text-align: center; font-size: 12px; color: #6b7280;">
        Professional Business Services | billing@company-suppliers.com | 1-800-555-0123
    </div>
</div>
            ''',
            'landing_page_content': 'This was a phishing simulation testing business email compromise awareness.'
        },

        {
            'name': 'HR Benefits Update',
            'description': 'A social engineering template impersonating HR with benefits information.',
            'category': 'hr',
            'difficulty_level': 'medium',
            'subject': 'Important: Annual Benefits Enrollment - Action Required by {{employee.first_name}}',
            'sender_name': 'Human Resources',
            'sender_email': 'hr@company.com',
            'html_content': '''
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
    <div style="background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%); color: white; padding: 20px; text-align: center;">
        <h1 style="margin: 0; font-size: 22px; font-weight: bold;">📋 Benefits Enrollment 2025</h1>
        <p style="margin: 5px 0 0 0; font-size: 14px;">Your benefits selection is required</p>
    </div>
    <div style="padding: 30px 20px;">
        <p style="color: #374151; margin-bottom: 15px;">Dear {{employee.first_name}},</p>

        <p style="color: #374151; margin-bottom: 15px;">
            It's that time of year again! Our annual benefits enrollment period is now open, and we need you to review and confirm your benefit selections for 2025.
        </p>

        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; margin: 20px 0;">
            <p style="margin: 0 0 10px 0; font-weight: bold; color: #166534;">✨ New for 2025:</p>
            <ul style="color: #166534; margin: 0; padding-left: 20px; font-size: 14px;">
                <li>Enhanced dental coverage with orthodontics</li>
                <li>Expanded mental health benefits</li>
                <li>New flexible spending account options</li>
                <li>Additional life insurance coverage</li>
            </ul>
        </div>

        <p style="color: #374151; margin-bottom: 20px;">
            <strong>Important:</strong> If you don't make your selections by the deadline, you will be automatically enrolled in the basic plan, which may not meet your needs.
        </p>

        <div style="background-color: #fffbeb; border: 1px solid #fcd34d; padding: 15px; margin: 20px 0; text-align: center;">
            <p style="margin: 0; color: #92400e; font-weight: bold;">⏰ Enrollment Deadline: January 31, 2025</p>
        </div>

        <p style="color: #374151; margin-bottom: 20px;">
            Please complete your enrollment by accessing our secure benefits portal:
        </p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{tracking_url}}" style="background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%); color: white; padding: 12px 25px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                Access Benefits Portal
            </a>
        </div>

        <div style="background-color: #f0f4ff; border: 1px solid #c7d2fe; padding: 15px; margin: 20px 0;">
            <p style="margin: 0 0 10px 0; font-weight: bold; color: #1e3a8a;">Need Help?</p>
            <p style="margin: 0; color: #374151; font-size: 14px;">
                Join our virtual benefits fair on January 25th at 2:00 PM, or contact HR at ext. 1234 with any questions.
            </p>
        </div>

        <p style="color: #374151; margin-bottom: 5px;">Thank you for taking the time to review your benefits.</p>
        <p style="color: #374151; margin-bottom: 5px;">Best regards,</p>
        <p style="color: #374151; margin: 0; font-weight: bold;">Human Resources Team</p>
    </div>
    <div style="background-color: #f8fafc; padding: 15px; text-align: center; font-size: 12px; color: #6b7280;">
        Company HR Department | hr@company.com | Employee Self-Service Portal
    </div>
</div>
            ''',
            'landing_page_content': 'This was a phishing simulation testing HR-related social engineering awareness.'
        },

        {
            'name': 'Package Delivery Notification',
            'description': 'A delivery notification template that creates urgency around package pickup.',
            'category': 'delivery',
            'difficulty_level': 'easy',
            'subject': 'Delivery Attempt Failed - Package Awaiting Pickup #PKG847291',
            'sender_name': 'Express Delivery Service',
            'sender_email': 'deliveries@express-shipping.com',
            'html_content': '''
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
    <div style="background-color: #1e3a8a; color: white; padding: 20px;">
        <div style="display: flex; align-items: center;">
            <div style="background-color: white; color: #1e3a8a; padding: 8px 12px; border-radius: 4px; margin-right: 15px; font-weight: bold;">
                📦 EDS
            </div>
            <div>
                <h1 style="margin: 0; font-size: 20px; font-weight: bold;">Express Delivery Service</h1>
                <p style="margin: 5px 0 0 0; font-size: 14px;">Package Delivery Notification</p>
            </div>
        </div>
    </div>
    <div style="padding: 30px 20px;">
        <p style="color: #374151; margin-bottom: 15px;">Dear {{employee.first_name}},</p>

        <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0;">
            <p style="margin: 0; color: #b91c1c; font-weight: bold;">
                ⚠️ DELIVERY ATTEMPT FAILED
            </p>
        </div>

        <p style="color: #374151; margin-bottom: 15px;">
            We attempted to deliver a package to your address today, but unfortunately, no one was available to receive it.
        </p>

        <div style="background-color: #f8fafc; border: 1px solid #e5e7eb; padding: 20px; margin: 20px 0;">
            <h3 style="margin: 0 0 15px 0; color: #1e3a8a;">Package Details:</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; color: #374151;">Tracking Number:</td>
                    <td style="padding: 8px 0; color: #374151;">PKG847291</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; color: #374151;">Delivery Address:</td>
                    <td style="padding: 8px 0; color: #374151;">{{employee.email}}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; color: #374151;">Attempt Date:</td>
                    <td style="padding: 8px 0; color: #374151;">Today, 2:15 PM</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; color: #374151;">Next Attempt:</td>
                    <td style="padding: 8px 0; color: #ef4444; font-weight: bold;">Will be returned to sender in 2 days</td>
                </tr>
            </table>
        </div>

        <p style="color: #374151; margin-bottom: 20px;">
            <strong>Important:</strong> Your package will be returned to the sender if not collected within 48 hours.
            Please arrange for redelivery or pickup immediately.
        </p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{tracking_url}}" style="background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%); color: white; padding: 12px 25px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                📦 Schedule Redelivery
            </a>
        </div>

        <div style="background-color: #f0f4ff; border: 1px solid #c7d2fe; padding: 15px; margin: 20px 0;">
            <p style="margin: 0 0 10px 0; font-weight: bold; color: #1e3a8a;">Alternative Options:</p>
            <ul style="color: #374151; margin: 0; padding-left: 20px; font-size: 14px;">
                <li>Pick up from our distribution center (123 Shipping Way)</li>
                <li>Authorize delivery to a neighbor</li>
                <li>Schedule delivery for a specific time</li>
            </ul>
        </div>

        <p style="color: #374151; font-size: 14px; margin-bottom: 20px;">
            For questions about your delivery, please contact our customer service team at 1-800-555-SHIP.
        </p>

        <p style="color: #374151; margin-bottom: 5px;">Thank you for choosing Express Delivery Service.</p>
        <p style="color: #374151; margin: 0; font-weight: bold;">Customer Service Team</p>
    </div>
    <div style="background-color: #f8fafc; padding: 15px; text-align: center; font-size: 12px; color: #6b7280;">
        Express Delivery Service | Track: tracking.express-shipping.com | Support: 1-800-555-SHIP
    </div>
</div>
            ''',
            'landing_page_content': 'This was a phishing simulation testing package delivery scam awareness.'
        }
    ]

    created_count = 0
    for template_data in default_templates:
        # Check if template already exists
        existing_template = EmailTemplate.query.filter_by(
            name=template_data['name'],
            is_system_template=True
        ).first()

        if existing_template:
            print(f"Template '{template_data['name']}' already exists, skipping...")
            continue

        # Create new template
        template = EmailTemplate(
            name=template_data['name'],
            description=template_data['description'],
            category=template_data['category'],
            difficulty_level=template_data['difficulty_level'],
            subject=template_data['subject'],
            sender_name=template_data['sender_name'],
            sender_email=template_data['sender_email'],
            html_content=template_data['html_content'],
            landing_page_content=template_data['landing_page_content'],
            is_system_template=True,
            created_by_id=admin_user.id,
            is_active=True
        )

        db.session.add(template)
        created_count += 1
        print(f"Created default template: {template_data['name']}")

    try:
        db.session.commit()
        print(f"Successfully created {created_count} default email templates!")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error creating default email templates: {e}")
        return False


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

        # Create default email templates
        create_default_email_templates()

        print("Database initialization completed!")
