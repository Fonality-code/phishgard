# Authentication System Documentation

## Overview

This Flask web application includes a comprehensive authentication system with Role-Based Access Control (RBAC) and relationship-based access control.

## Features

### Authentication
- User registration with comprehensive profile information
- Secure login/logout functionality
- Password change capability
- Session management with Flask-Login

### Role-Based Access Control (RBAC)
- **Roles**: Admin, Manager, User, Customer, Business
- **Permissions**: Fine-grained permissions for different resources and actions
- **Dynamic Assignment**: Roles and permissions can be assigned dynamically

### Relationship-Based Access Control
- **User Relationships**: Manager-employee, parent company-subsidiary relationships
- **Hierarchical Access**: Users can access resources based on their relationships
- **Flexible Relationship Types**: Support for custom relationship types

### User Management
- **Profile Management**: Complete user profile with personal and business information
- **Account Types**: Customer, Business, or Both
- **Multi-language Support**: Preferred language settings
- **Location Information**: Country, city, and address

## Database Models

### User Model
- Personal information (name, email, phone, date of birth)
- Location information (country, city, address)
- Account settings (type, status, language preference)
- Business information (for business accounts)
- Timestamps and login tracking

### RBAC Models
- **Role**: Named roles with descriptions and system flags
- **Permission**: Resource-action based permissions
- **UserRelationship**: Parent-child relationships between users
- **AccessControl**: Fine-grained access control entries

## Setup Instructions

### 1. Install Dependencies
```bash
uv sync
```

### 2. Initialize Database
```bash
python init_db.py
```

This will:
- Create all database tables
- Initialize default roles and permissions
- Create an admin user
- Assign default roles to existing users

### 3. Run the Application
```bash
python run.py
```

## Default Roles and Permissions

### Admin Role
- Full system administration
- User management (create, read, update, delete, list)
- Role management (create, read, update, delete, assign)
- Permission management
- Relationship management
- Access control management

### Manager Role
- User read, update, and list permissions
- Relationship management
- Access control read permissions
- System monitoring

### User Role
- Basic user read permissions (own profile)

### Customer Role
- Basic customer permissions

### Business Role
- User read and update permissions

## Usage Examples

### Checking Permissions in Views
```python
from app.utils.rbac_manager import require_permission, require_role

@app.route('/admin/users')
@require_role('admin')
def admin_users():
    # Only admins can access this
    pass

@app.route('/user/<int:user_id>')
@require_permission('user.read', 'user')
def user_detail(user_id):
    # Checks if user has permission to read user data
    pass
```

### Checking Permissions in Templates
```html
{% if current_user.has_role('admin') %}
    <a href="{{ url_for('auth.admin') }}">Admin Dashboard</a>
{% endif %}

{% if current_user.has_permission('user.create') %}
    <a href="{{ url_for('auth.create_user') }}">Create User</a>
{% endif %}
```

### Managing Relationships
```python
from app.utils.rbac_manager import RBACManager

# Create a manager-employee relationship
RBACManager.create_user_relationship(
    parent_user=manager,
    child_user=employee,
    relationship_type='manager',
    created_by=admin_user
)

# Grant specific access
RBACManager.grant_access(
    user=user,
    permission=read_permission,
    resource_type='user',
    resource_id=target_user_id,
    granted_by=admin_user
)
```

## API Endpoints

### Authentication
- `GET/POST /auth/login` - User login
- `GET/POST /auth/register` - User registration
- `GET /auth/logout` - User logout
- `GET /auth/profile` - User profile
- `GET/POST /auth/change-password` - Change password

### Admin
- `GET /auth/admin` - Admin dashboard
- `GET /auth/admin/users/<int:user_id>` - User detail page

## Security Features

### Password Security
- Minimum 8 character requirement
- Password hashing with Werkzeug
- Secure password confirmation

### Session Security
- Flask-Login session management
- Configurable session timeouts
- Remember me functionality

### Access Control
- Permission-based view protection
- Relationship-based access control
- Resource-level permissions

## Customization

### Adding New Roles
```python
role = RBACManager.create_role(
    name='custom_role',
    description='Custom role description'
)
```

### Adding New Permissions
```python
permission = RBACManager.create_permission(
    name='resource.action',
    description='Permission description',
    resource='resource_name',
    action='action_name'
)
```

### Custom Relationship Types
Relationships support custom types like:
- `manager` - Manager-employee relationship
- `parent_company` - Parent-subsidiary relationship
- `team_lead` - Team leader relationship
- Any custom type you define

## Development Notes

### Template Structure
- Simple HTML templates without styling frameworks
- Bootstrap-like CSS classes for basic styling
- Responsive design considerations
- Flash message support

### Form Validation
- Flask-WTF form validation
- Client-side validation hints
- Comprehensive error handling

### Internationalization
- Flask-Babel integration
- Multi-language support
- Translatable strings

## Troubleshooting

### Common Issues

1. **Database not initialized**: Run `python init_db.py`
2. **Permission denied errors**: Check user roles and permissions
3. **Template not found**: Ensure all template files are in place
4. **Import errors**: Verify all dependencies are installed

### Debug Mode
Enable debug mode in development:
```python
app.run(debug=True)
```

## Production Considerations

### Security
- Use strong secret keys
- Enable HTTPS
- Configure secure session cookies
- Regular security audits

### Performance
- Database indexing on frequently queried fields
- Session store optimization
- Caching strategies

### Monitoring
- Log authentication events
- Monitor failed login attempts
- Track permission usage
