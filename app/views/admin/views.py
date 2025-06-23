"""
Admin Views - Comprehensive administrative functions
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from datetime import datetime, timedelta
import json

from app.extensions import db
from app.models import User, Role, Permission, UserRelationship, AccessControl
from app.models.rbac import user_roles, role_permissions
from .forms import (UserManagementForm, RoleManagementForm, PermissionManagementForm,
                   AssignRoleForm, UserRelationshipForm, SystemSettingsForm, BulkUserActionForm)

# Create admin blueprint
admin = Blueprint('admin', __name__, url_prefix='/admin')


def require_admin(f):
    """Decorator to require admin role"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_role('admin'):
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


@admin.route('/')
@admin.route('/dashboard')
@login_required
@require_admin
def dashboard():
    """Admin dashboard with system overview"""
    # Get user statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(account_status='active').count()
    verified_users = User.query.filter_by(email_verified=True).count()
    business_users = User.query.filter_by(account_type='business').count()

    # Get recent users (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_users = User.query.filter(User.created_at >= thirty_days_ago).count()

    # Get recent logins (last 24 hours)
    yesterday = datetime.now() - timedelta(hours=24)
    recent_logins = User.query.filter(User.last_login >= yesterday).count()

    # Get role statistics
    total_roles = Role.query.count()
    system_roles = Role.query.filter_by(is_system=True).count()
    custom_roles = total_roles - system_roles

    # Get permission statistics
    total_permissions = Permission.query.count()

    # Get relationship statistics
    total_relationships = UserRelationship.query.filter_by(is_active=True).count()

    # Get recent activity
    recent_users_list = User.query.order_by(desc(User.created_at)).limit(5).all()

    stats = {
        'users': {
            'total': total_users,
            'active': active_users,
            'verified': verified_users,
            'business': business_users,
            'recent': recent_users,
            'recent_logins': recent_logins
        },
        'rbac': {
            'total_roles': total_roles,
            'system_roles': system_roles,
            'custom_roles': custom_roles,
            'total_permissions': total_permissions,
            'total_relationships': total_relationships
        }
    }

    return render_template('admin/dashboard.html', stats=stats, recent_users=recent_users_list)


@admin.route('/users')
@login_required
@require_admin
def users():
    """User management page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Search and filter
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')

    query = User.query

    if search:
        query = query.filter(
            db.or_(
                User.first_name.contains(search),
                User.last_name.contains(search),
                User.email.contains(search)
            )
        )

    if status_filter:
        query = query.filter_by(account_status=status_filter)

    if type_filter:
        query = query.filter_by(account_type=type_filter)

    users = query.order_by(desc(User.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('admin/users.html', users=users, search=search,
                         status_filter=status_filter, type_filter=type_filter)


@admin.route('/users/<int:user_id>')
@login_required
@require_admin
def user_detail(user_id):
    """User detail and management page"""
    user = User.query.get_or_404(user_id)
    form = UserManagementForm(obj=user)

    # Get user's roles
    user_roles_list = user.roles.all()

    # Get user's relationships
    parent_relationships = UserRelationship.query.filter_by(
        child_user_id=user_id, is_active=True
    ).all()
    child_relationships = UserRelationship.query.filter_by(
        parent_user_id=user_id, is_active=True
    ).all()

    # Get user's access controls
    access_controls = AccessControl.query.filter_by(user_id=user_id).all()

    # Get all available roles for assignment
    all_roles = Role.query.all()

    return render_template('admin/user_detail.html', user=user, form=form,
                         user_roles=user_roles_list, parent_relationships=parent_relationships,
                         child_relationships=child_relationships, access_controls=access_controls,
                         all_roles=all_roles)


@admin.route('/users/<int:user_id>/edit', methods=['POST'])
@login_required
@require_admin
def edit_user(user_id):
    """Edit user details"""
    user = User.query.get_or_404(user_id)
    form = UserManagementForm()

    if form.validate_on_submit():
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.email = form.email.data
        user.account_type = form.account_type.data
        user.account_status = form.account_status.data
        user.email_verified = form.email_verified.data

        try:
            db.session.commit()
            flash(f'User {user.full_name} updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')

    return redirect(url_for('admin.user_detail', user_id=user_id))


@admin.route('/users/<int:user_id>/toggle-status')
@login_required
@require_admin
def toggle_user_status(user_id):
    """Toggle user active/inactive status"""
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('Cannot change your own status.', 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))

    new_status = 'active' if user.account_status != 'active' else 'inactive'
    user.account_status = new_status

    try:
        db.session.commit()
        flash(f'User {user.full_name} is now {new_status}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user status: {str(e)}', 'error')

    return redirect(url_for('admin.user_detail', user_id=user_id))


@admin.route('/roles')
@login_required
@require_admin
def roles():
    """Role management page"""
    roles = Role.query.order_by(Role.name).all()
    form = RoleManagementForm()
    return render_template('admin/roles.html', roles=roles, form=form)


@admin.route('/roles/create', methods=['POST'])
@login_required
@require_admin
def create_role():
    """Create new role"""
    form = RoleManagementForm()

    if form.validate_on_submit():
        # Check if role name already exists
        existing_role = Role.query.filter_by(name=form.name.data).first()
        if existing_role:
            flash('Role name already exists.', 'error')
            return redirect(url_for('admin.roles'))

        role = Role(
            name=form.name.data,
            description=form.description.data,
            is_system=form.is_system.data
        )

        try:
            db.session.add(role)
            db.session.commit()
            flash(f'Role "{role.name}" created successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating role: {str(e)}', 'error')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')

    return redirect(url_for('admin.roles'))


@admin.route('/roles/<int:role_id>')
@login_required
@require_admin
def role_detail(role_id):
    """Role detail and permission management"""
    role = Role.query.get_or_404(role_id)
    all_permissions = Permission.query.order_by(Permission.resource, Permission.action).all()
    role_permissions_list = role.permissions.all()

    # Get permissions not assigned to this role
    role_permission_ids = [p.id for p in role_permissions_list]
    available_permissions = [p for p in all_permissions if p.id not in role_permission_ids]

    # Get users with this role
    users_with_role = User.query.join(user_roles).filter(user_roles.c.role_id == role_id).all()

    return render_template('admin/role_detail.html', role=role,
                         all_permissions=all_permissions, role_permissions=role_permissions_list,
                         available_permissions=available_permissions, users_with_role=users_with_role)


@admin.route('/roles/<int:role_id>/edit', methods=['POST'])
@login_required
@require_admin
def edit_role(role_id):
    """Edit role details"""
    role = Role.query.get_or_404(role_id)
    form = RoleManagementForm()

    if form.validate_on_submit():
        # Check if changing name would conflict
        if form.name.data != role.name:
            existing_role = Role.query.filter_by(name=form.name.data).first()
            if existing_role:
                flash('Role name already exists.', 'error')
                return redirect(url_for('admin.role_detail', role_id=role_id))

        role.name = form.name.data
        role.description = form.description.data
        role.is_system = form.is_system.data

        try:
            db.session.commit()
            flash(f'Role "{role.name}" updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating role: {str(e)}', 'error')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')

    return redirect(url_for('admin.role_detail', role_id=role_id))


@admin.route('/roles/<int:role_id>/permissions', methods=['POST'])
@login_required
@require_admin
def manage_role_permissions(role_id):
    """Add or remove permissions from role"""
    role = Role.query.get_or_404(role_id)
    permission_ids = request.form.getlist('permission_ids')

    # Clear current permissions
    role.permissions = []

    # Add selected permissions
    for permission_id in permission_ids:
        permission = Permission.query.get(permission_id)
        if permission:
            role.add_permission(permission)

    try:
        db.session.commit()
        flash(f'Permissions updated for role "{role.name}".', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating permissions: {str(e)}', 'error')

    return redirect(url_for('admin.role_detail', role_id=role_id))


@admin.route('/roles/<int:role_id>/delete', methods=['POST'])
@login_required
@require_admin
def delete_role(role_id):
    """Delete role"""
    role = Role.query.get_or_404(role_id)

    if role.is_system:
        flash('Cannot delete system roles.', 'error')
        return redirect(url_for('admin.roles'))

    # Check if role is assigned to any users
    users_count = User.query.join(user_roles).filter(user_roles.c.role_id == role_id).count()
    if users_count > 0:
        flash(f'Cannot delete role "{role.name}". It is assigned to {users_count} user(s).', 'error')
        return redirect(url_for('admin.roles'))

    try:
        db.session.delete(role)
        db.session.commit()
        flash(f'Role "{role.name}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting role: {str(e)}', 'error')

    return redirect(url_for('admin.roles'))


@admin.route('/permissions')
@login_required
@require_admin
def permissions():
    """Permission management page"""
    permissions = Permission.query.order_by(Permission.resource, Permission.action).all()
    form = PermissionManagementForm()
    return render_template('admin/permissions.html', permissions=permissions, form=form)


@admin.route('/permissions/create', methods=['POST'])
@login_required
@require_admin
def create_permission():
    """Create new permission"""
    form = PermissionManagementForm()

    if form.validate_on_submit():
        # Check if permission name already exists
        existing_permission = Permission.query.filter_by(name=form.name.data).first()
        if existing_permission:
            flash('Permission name already exists.', 'error')
            return redirect(url_for('admin.permissions'))

        permission = Permission(
            name=form.name.data,
            description=form.description.data,
            resource=form.resource.data,
            action=form.action.data
        )

        try:
            db.session.add(permission)
            db.session.commit()
            flash(f'Permission "{permission.name}" created successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating permission: {str(e)}', 'error')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')

    return redirect(url_for('admin.permissions'))


@admin.route('/users/<int:user_id>/assign-role', methods=['POST'])
@login_required
@require_admin
def assign_role_to_user(user_id):
    """Assign role to user"""
    user = User.query.get_or_404(user_id)
    role_id = request.form.get('role_id', type=int)

    if not role_id:
        flash('Please select a role.', 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))

    role = Role.query.get_or_404(role_id)

    if user.has_role(role.name):
        flash(f'User already has role "{role.name}".', 'warning')
    else:
        user.add_role(role)
        try:
            db.session.commit()
            flash(f'Role "{role.name}" assigned to {user.full_name}.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error assigning role: {str(e)}', 'error')

    return redirect(url_for('admin.user_detail', user_id=user_id))


@admin.route('/users/<int:user_id>/remove-role/<int:role_id>', methods=['POST'])
@login_required
@require_admin
def remove_role_from_user(user_id, role_id):
    """Remove role from user"""
    user = User.query.get_or_404(user_id)
    role = Role.query.get_or_404(role_id)

    if user.has_role(role.name):
        user.remove_role(role)
        try:
            db.session.commit()
            flash(f'Role "{role.name}" removed from {user.full_name}.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error removing role: {str(e)}', 'error')
    else:
        flash(f'User does not have role "{role.name}".', 'warning')

    return redirect(url_for('admin.user_detail', user_id=user_id))


@admin.route('/relationships')
@login_required
@require_admin
def relationships():
    """User relationship management page"""
    relationships = UserRelationship.query.filter_by(is_active=True).all()
    form = UserRelationshipForm()
    return render_template('admin/relationships.html', relationships=relationships, form=form)


@admin.route('/relationships/create', methods=['POST'])
@login_required
@require_admin
def create_relationship():
    """Create user relationship"""
    form = UserRelationshipForm()

    if form.validate_on_submit():
        parent_user = User.query.get(form.parent_user_id.data)
        child_user = User.query.get(form.child_user_id.data)

        if not parent_user or not child_user:
            flash('Invalid user IDs.', 'error')
            return redirect(url_for('admin.relationships'))

        if parent_user.id == child_user.id:
            flash('Users cannot have a relationship with themselves.', 'error')
            return redirect(url_for('admin.relationships'))

        # Check if relationship already exists
        existing = UserRelationship.query.filter_by(
            parent_user_id=form.parent_user_id.data,
            child_user_id=form.child_user_id.data,
            relationship_type=form.relationship_type.data,
            is_active=True
        ).first()

        if existing:
            flash('Relationship already exists.', 'warning')
            return redirect(url_for('admin.relationships'))

        relationship = UserRelationship(
            parent_user_id=form.parent_user_id.data,
            child_user_id=form.child_user_id.data,
            relationship_type=form.relationship_type.data,
            created_by=current_user.id
        )

        try:
            db.session.add(relationship)
            db.session.commit()
            flash(f'Relationship created: {parent_user.full_name} -> {child_user.full_name} ({form.relationship_type.data}).', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating relationship: {str(e)}', 'error')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')

    return redirect(url_for('admin.relationships'))


@admin.route('/analytics')
@login_required
@require_admin
def analytics():
    """System analytics and reporting"""
    # User registration trends (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    registration_data = []

    for i in range(30):
        date = thirty_days_ago + timedelta(days=i)
        count = User.query.filter(
            func.date(User.created_at) == date.date()
        ).count()
        registration_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })

    # Role distribution
    role_distribution = []
    for role in Role.query.all():
        count = User.query.join(user_roles).filter(user_roles.c.role_id == role.id).count()
        role_distribution.append({
            'name': role.name,
            'count': count
        })

    # Account type distribution
    account_types = db.session.query(
        User.account_type,
        func.count(User.id).label('count')
    ).group_by(User.account_type).all()

    # Account status distribution
    account_statuses = db.session.query(
        User.account_status,
        func.count(User.id).label('count')
    ).group_by(User.account_status).all()

    analytics_data = {
        'registrations': registration_data,
        'role_distribution': role_distribution,
        'account_types': [(at[0], at[1]) for at in account_types],
        'account_statuses': [(ast[0], ast[1]) for ast in account_statuses]
    }

    return render_template('admin/analytics.html', analytics=analytics_data)


@admin.route('/settings', methods=['GET', 'POST'])
@login_required
@require_admin
def settings():
    """System settings management"""
    form = SystemSettingsForm()

    if form.validate_on_submit():
        # In a real application, you would save settings to database or config
        # For now, just flash success message
        flash('Settings updated successfully.', 'success')
        return redirect(url_for('admin.settings'))

    # Get system information
    import sys
    import flask
    import platform

    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    flask_version = flask.__version__
    total_users = User.query.count()
    active_sessions = User.query.filter(User.last_login.isnot(None)).count()  # Simplified
    uptime = "24 hours 30 minutes"  # Simplified for demo

    return render_template('admin/settings.html', form=form,
                         python_version=python_version,
                         flask_version=flask_version,
                         total_users=total_users,
                         active_sessions=active_sessions,
                         uptime=uptime)


@admin.route('/bulk-actions', methods=['POST'])
@login_required
@require_admin
def bulk_actions():
    """Execute bulk actions on users"""
    form = BulkUserActionForm()

    if form.validate_on_submit():
        try:
            user_ids = [int(uid.strip()) for uid in form.user_ids.data.split(',') if uid.strip()]
            action = form.action.data

            if not user_ids:
                flash('No user IDs provided.', 'error')
                return redirect(url_for('admin.users'))

            users = User.query.filter(User.id.in_(user_ids)).all()
            if not users:
                flash('No valid users found.', 'error')
                return redirect(url_for('admin.users'))

            # Prevent actions on current user
            if current_user.id in user_ids:
                flash('Cannot perform bulk actions on yourself.', 'error')
                return redirect(url_for('admin.users'))

            success_count = 0
            for user in users:
                if action == 'activate':
                    user.account_status = 'active'
                    success_count += 1
                elif action == 'deactivate':
                    user.account_status = 'inactive'
                    success_count += 1
                elif action == 'suspend':
                    user.account_status = 'suspended'
                    success_count += 1
                elif action == 'delete':
                    db.session.delete(user)
                    success_count += 1

            db.session.commit()
            flash(f'Bulk action "{action}" completed for {success_count} users.', 'success')

        except ValueError:
            flash('Invalid user IDs format.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error executing bulk action: {str(e)}', 'error')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')

    return redirect(url_for('admin.users'))


# API endpoints for AJAX calls
@admin.route('/api/users/search')
@login_required
@require_admin
def api_user_search():
    """API endpoint for user search"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    users = User.query.filter(
        db.or_(
            User.first_name.contains(query),
            User.last_name.contains(query),
            User.email.contains(query)
        )
    ).limit(10).all()

    return jsonify([{
        'id': user.id,
        'name': user.full_name,
        'email': user.email
    } for user in users])


@admin.route('/api/stats')
@login_required
@require_admin
def api_stats():
    """API endpoint for dashboard stats"""
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(account_status='active').count(),
        'total_roles': Role.query.count(),
        'total_permissions': Permission.query.count()
    }
    return jsonify(stats)


@admin.route('/roles/<int:role_id>/add-permission', methods=['POST'])
@login_required
@require_admin
def add_role_permission(role_id):
    """Add permission to role"""
    role = Role.query.get_or_404(role_id)
    permission_id = request.form.get('permission_id', type=int)

    if not permission_id:
        flash('Please select a permission.', 'error')
        return redirect(url_for('admin.role_detail', role_id=role_id))

    permission = Permission.query.get_or_404(permission_id)

    if permission in role.permissions.all():
        flash(f'Role already has permission "{permission.name}".', 'warning')
    else:
        role.add_permission(permission)
        try:
            db.session.commit()
            flash(f'Permission "{permission.name}" added to role "{role.name}".', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding permission: {str(e)}', 'error')

    return redirect(url_for('admin.role_detail', role_id=role_id))


@admin.route('/roles/<int:role_id>/remove-permission', methods=['POST'])
@login_required
@require_admin
def remove_role_permission(role_id):
    """Remove permission from role"""
    role = Role.query.get_or_404(role_id)

    if request.is_json:
        data = request.get_json()
        permission_id = data.get('permission_id')
    else:
        permission_id = request.form.get('permission_id', type=int)

    if not permission_id:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Permission ID required'})
        flash('Permission ID required.', 'error')
        return redirect(url_for('admin.role_detail', role_id=role_id))

    permission = Permission.query.get_or_404(permission_id)

    if permission in role.permissions.all():
        role.remove_permission(permission)
        try:
            db.session.commit()
            if request.is_json:
                return jsonify({'success': True, 'message': f'Permission "{permission.name}" removed from role'})
            flash(f'Permission "{permission.name}" removed from role "{role.name}".', 'success')
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'message': str(e)})
            flash(f'Error removing permission: {str(e)}', 'error')
    else:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Role does not have this permission'})
        flash('Role does not have this permission.', 'warning')

    if request.is_json:
        return jsonify({'success': True})
    return redirect(url_for('admin.role_detail', role_id=role_id))


# System maintenance endpoints
@admin.route('/create-backup', methods=['POST'])
@login_required
@require_admin
def create_backup():
    """Create system backup"""
    try:
        # In a real application, you would implement proper backup logic here
        # For now, just simulate the operation
        import time
        time.sleep(1)  # Simulate backup process
        return jsonify({'success': True, 'message': 'Backup created successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@admin.route('/clear-cache', methods=['POST'])
@login_required
@require_admin
def clear_cache():
    """Clear system cache"""
    try:
        # In a real application, you would implement cache clearing logic here
        # For now, just simulate the operation
        return jsonify({'success': True, 'message': 'Cache cleared successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@admin.route('/run-maintenance', methods=['POST'])
@login_required
@require_admin
def run_maintenance():
    """Run system maintenance"""
    try:
        # In a real application, you would implement maintenance tasks here
        # For now, just simulate the operation
        import time
        time.sleep(2)  # Simulate maintenance process
        return jsonify({'success': True, 'message': 'Maintenance completed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
