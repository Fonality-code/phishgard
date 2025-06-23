"""
Authentication forms
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SelectField, BooleanField, TextAreaField, DateField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from wtforms.widgets import TextArea


class LoginForm(FlaskForm):
    """Login form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')


class RegistrationForm(FlaskForm):
    """Registration form"""
    # Personal information
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    date_of_birth = DateField('Date of Birth', validators=[Optional()])

    # Profile image
    profile_image = FileField('Profile Image', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Images only!')
    ])

    # Location
    country = SelectField('Country', validators=[DataRequired()], choices=[
        ('CM', 'Cameroon'),

    ])
    city = StringField('City', validators=[DataRequired(), Length(min=2, max=100)])
    address = StringField('Address', validators=[Optional(), Length(max=200)])

    # Account settings
    preferred_language = SelectField('Preferred Language', validators=[DataRequired()], choices=[
        ('en', 'English'),
        ('fr', 'Français'),
    ])
    account_type = SelectField('Account Type', validators=[DataRequired()], choices=[
        ('customer', 'Customer'),
        ('business', 'Business'),
        ('both', 'Customer & Business'),
    ])

    # Business information (optional)
    business_name = StringField('Business Name', validators=[Optional(), Length(max=100)])
    business_type = SelectField('Business Type', validators=[Optional()], choices=[
        ('', 'Select Business Type'),
        ('retail', 'Retail'),
        ('restaurant', 'Restaurant'),
        ('service', 'Service'),
        ('manufacturing', 'Manufacturing'),
        ('technology', 'Technology'),
        ('healthcare', 'Healthcare'),
        ('education', 'Education'),
        ('finance', 'Finance'),
        ('real_estate', 'Real Estate'),
        ('other', 'Other'),
    ])
    business_description = TextAreaField('Business Description', validators=[Optional()], widget=TextArea())
    website_url = StringField('Website URL', validators=[Optional(), Length(max=200)])

    # Password
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    password_confirm = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])


class ChangePasswordForm(FlaskForm):
    """Change password form"""
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    new_password_confirm = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ])


class ForgotPasswordForm(FlaskForm):
    """Forgot password form"""
    email = StringField('Email', validators=[DataRequired(), Email()])


class ResetPasswordForm(FlaskForm):
    """Reset password form"""
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    password_confirm = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])


class ProfileUpdateForm(FlaskForm):
    """Profile update form"""
    # Personal information
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    phone_number = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    date_of_birth = DateField('Date of Birth', validators=[Optional()])

    # Profile image
    profile_image = FileField('Profile Image', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Images only!')
    ])
    remove_profile_image = BooleanField('Remove Current Profile Image')

    # Location
    country = SelectField('Country', validators=[DataRequired()], choices=[
        ('CM', 'Cameroon'),

    ])
    city = StringField('City', validators=[DataRequired(), Length(min=2, max=100)])
    address = StringField('Address', validators=[Optional(), Length(max=200)])

    # Account settings
    preferred_language = SelectField('Preferred Language', validators=[DataRequired()], choices=[
        ('en', 'English'),
        ('fr', 'Français'),

    ])

    # Business information (optional)
    business_name = StringField('Business Name', validators=[Optional(), Length(max=100)])
    business_type = SelectField('Business Type', validators=[Optional()], choices=[
        ('', 'Select Business Type'),
        ('retail', 'Retail'),
        ('restaurant', 'Restaurant'),
        ('service', 'Service'),
        ('manufacturing', 'Manufacturing'),
        ('technology', 'Technology'),
        ('healthcare', 'Healthcare'),
        ('education', 'Education'),
        ('finance', 'Finance'),
        ('real_estate', 'Real Estate'),
        ('other', 'Other'),
    ])
    business_description = TextAreaField('Business Description', validators=[Optional()], widget=TextArea())
    website_url = StringField('Website URL', validators=[Optional(), Length(max=200)])
