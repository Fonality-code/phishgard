"""
Admin Forms
"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Email, URL, NumberRange
from app.models import Role, Permission


class UserManagementForm(FlaskForm):
    """Form for managing users"""
    first_name = StringField('First Name', validators=[DataRequired(), Length(1, 64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(1, 64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(1, 120)])
    account_type = SelectField('Account Type',
                              choices=[('individual', 'Individual'), ('business', 'Business')],
                              validators=[DataRequired()])
    account_status = SelectField('Account Status',
                                choices=[('active', 'Active'), ('inactive', 'Inactive'), ('suspended', 'Suspended')],
                                validators=[DataRequired()])
    email_verified = BooleanField('Email Verified')
    submit = SubmitField('Update User')


class RoleManagementForm(FlaskForm):
    """Form for managing roles"""
    name = StringField('Role Name', validators=[DataRequired(), Length(1, 64)])
    description = TextAreaField('Description', validators=[Optional(), Length(0, 255)])
    is_system = BooleanField('System Role')
    submit = SubmitField('Save Role')


class PermissionManagementForm(FlaskForm):
    """Form for managing permissions"""
    name = StringField('Permission Name', validators=[DataRequired(), Length(1, 64)])
    description = TextAreaField('Description', validators=[Optional(), Length(0, 255)])
    resource = StringField('Resource', validators=[DataRequired(), Length(1, 64)])
    action = SelectField('Action',
                        choices=[('create', 'Create'), ('read', 'Read'), ('update', 'Update'), ('delete', 'Delete')],
                        validators=[DataRequired()])
    submit = SubmitField('Save Permission')


class AssignRoleForm(FlaskForm):
    """Form for assigning roles to users"""
    user_id = IntegerField('User ID', validators=[DataRequired()])
    role_id = SelectField('Role', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Assign Role')

    def __init__(self, *args, **kwargs):
        super(AssignRoleForm, self).__init__(*args, **kwargs)
        self.role_id.choices = [(role.id, role.name) for role in Role.query.all()]


class UserRelationshipForm(FlaskForm):
    """Form for managing user relationships"""
    parent_user_id = IntegerField('Parent User ID', validators=[DataRequired()])
    child_user_id = IntegerField('Child User ID', validators=[DataRequired()])
    relationship_type = SelectField('Relationship Type',
                                   choices=[('manager', 'Manager'), ('parent_company', 'Parent Company'),
                                          ('team_lead', 'Team Lead'), ('supervisor', 'Supervisor')],
                                   validators=[DataRequired()])
    submit = SubmitField('Create Relationship')


class SystemSettingsForm(FlaskForm):
    """Form for system settings"""
    # Site Settings
    site_name = StringField('Site Name', validators=[DataRequired(), Length(1, 100)])
    site_description = TextAreaField('Site Description', validators=[Optional(), Length(0, 500)])
    contact_email = StringField('Contact Email', validators=[DataRequired(), Email()])

    # Security Settings
    max_login_attempts = IntegerField('Maximum Login Attempts', validators=[DataRequired(), NumberRange(min=1, max=10)], default=5)
    session_timeout = IntegerField('Session Timeout (minutes)', validators=[DataRequired(), NumberRange(min=5, max=1440)], default=60)
    require_email_verification = BooleanField('Require Email Verification')
    enable_registration = BooleanField('Enable User Registration', default=True)

    # Maintenance
    maintenance_mode = BooleanField('Maintenance Mode')
    maintenance_message = TextAreaField('Maintenance Message', validators=[Optional(), Length(0, 500)])

    submit = SubmitField('Save Settings')


class BulkUserActionForm(FlaskForm):
    """Form for bulk user actions"""
    action = SelectField('Action',
                        choices=[('activate', 'Activate'), ('deactivate', 'Deactivate'),
                               ('suspend', 'Suspend'), ('delete', 'Delete')],
                        validators=[DataRequired()])
    user_ids = StringField('User IDs (comma-separated)', validators=[DataRequired()])
    submit = SubmitField('Execute Action')
