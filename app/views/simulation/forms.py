"""
Simulation Forms

Forms for phishing simulation functionality including campaigns, employees, and templates.
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import (
    StringField, TextAreaField, SelectField, SelectMultipleField,
    BooleanField, IntegerField, DateTimeField, EmailField
)
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange
from wtforms.widgets import TextArea
from app.models.simulation import EmailTemplate, Employee


class CampaignForm(FlaskForm):
    """Form for creating/editing campaigns"""
    name = StringField('Campaign Name', validators=[
        DataRequired(),
        Length(min=3, max=100)
    ])

    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500)
    ])

    email_template_id = SelectField('Email Template',
                                   validators=[DataRequired()],
                                   coerce=int)

    employee_ids = SelectMultipleField('Target Employees',
                                      validators=[DataRequired()],
                                      coerce=int)

    scheduled_start = DateTimeField('Scheduled Start Time',
                                   validators=[Optional()],
                                   format='%Y-%m-%d %H:%M')

    send_interval_minutes = IntegerField('Send Interval (minutes)',
                                        validators=[Optional(), NumberRange(min=0, max=1440)],
                                        default=0,
                                        description='0 = send all at once')

    track_opens = BooleanField('Track Email Opens', default=True)
    track_clicks = BooleanField('Track Link Clicks', default=True)
    capture_credentials = BooleanField('Capture Credentials', default=False)


class EmployeeForm(FlaskForm):
    """Form for creating/editing employees"""
    email = EmailField('Email Address', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])

    first_name = StringField('First Name', validators=[
        DataRequired(),
        Length(min=1, max=50)
    ])

    last_name = StringField('Last Name', validators=[
        DataRequired(),
        Length(min=1, max=50)
    ])

    department = StringField('Department', validators=[
        Optional(),
        Length(max=100)
    ])

    position = StringField('Position', validators=[
        Optional(),
        Length(max=100)
    ])

    employee_id = StringField('Employee ID', validators=[
        Optional(),
        Length(max=50)
    ])


class BulkEmployeeUploadForm(FlaskForm):
    """Form for bulk uploading employees via CSV"""
    csv_file = FileField('CSV File', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])


class EmailTemplateForm(FlaskForm):
    """Form for creating/editing email templates"""
    name = StringField('Template Name', validators=[
        DataRequired(),
        Length(min=3, max=100)
    ])

    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500)
    ])

    category = SelectField('Category', validators=[DataRequired()], choices=[
        ('social_engineering', 'Social Engineering'),
        ('urgent', 'Urgent/Time Sensitive'),
        ('finance', 'Financial'),
        ('it_support', 'IT Support'),
        ('hr', 'Human Resources'),
        ('delivery', 'Package Delivery'),
        ('security_alert', 'Security Alert'),
        ('other', 'Other')
    ])

    difficulty_level = SelectField('Difficulty Level', validators=[DataRequired()], choices=[
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ])

    subject = StringField('Email Subject', validators=[
        DataRequired(),
        Length(min=1, max=200)
    ])

    sender_name = StringField('Sender Name', validators=[
        DataRequired(),
        Length(min=1, max=100)
    ])

    sender_email = EmailField('Sender Email', validators=[
        DataRequired(),
        Email(),
        Length(max=100)
    ])

    html_content = TextAreaField('HTML Content', validators=[
        DataRequired()
    ], widget=TextArea())

    text_content = TextAreaField('Text Content', validators=[
        Optional()
    ])

    landing_page_url = StringField('Landing Page URL', validators=[
        Optional(),
        Length(max=500)
    ])

    landing_page_content = TextAreaField('Landing Page Content', validators=[
        Optional()
    ])


class TrainingModuleForm(FlaskForm):
    """Form for creating/editing training modules"""
    title = StringField('Module Title', validators=[
        DataRequired(),
        Length(min=3, max=200)
    ])

    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500)
    ])

    content = TextAreaField('Module Content', validators=[
        DataRequired()
    ])

    category = SelectField('Category', validators=[DataRequired()], choices=[
        ('phishing_basics', 'Phishing Basics'),
        ('email_security', 'Email Security'),
        ('social_engineering', 'Social Engineering'),
        ('password_security', 'Password Security'),
        ('safe_browsing', 'Safe Browsing'),
        ('incident_response', 'Incident Response'),
        ('data_protection', 'Data Protection'),
        ('other', 'Other')
    ])

    difficulty_level = SelectField('Difficulty Level', validators=[DataRequired()], choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced')
    ])

    estimated_duration = IntegerField('Estimated Duration (minutes)', validators=[
        DataRequired(),
        NumberRange(min=1, max=180)
    ])

    video_url = StringField('Video URL', validators=[
        Optional(),
        Length(max=500)
    ])


class CampaignFilterForm(FlaskForm):
    """Form for filtering campaigns"""
    status = SelectField('Status', choices=[
        ('', 'All Statuses'),
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled')
    ])

    template_category = SelectField('Template Category', choices=[
        ('', 'All Categories'),
        ('social_engineering', 'Social Engineering'),
        ('urgent', 'Urgent/Time Sensitive'),
        ('finance', 'Financial'),
        ('it_support', 'IT Support'),
        ('hr', 'Human Resources'),
        ('delivery', 'Package Delivery'),
        ('security_alert', 'Security Alert'),
        ('other', 'Other')
    ])


class EmployeeFilterForm(FlaskForm):
    """Form for filtering employees"""
    department = SelectField('Department', choices=[])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Dynamically populate department choices
        from app.models.simulation import Employee
        departments = Employee.query.with_entities(Employee.department).distinct().all()
        self.department.choices = [('', 'All Departments')] + [
            (dept[0], dept[0]) for dept in departments if dept[0]
        ]


class LinkAnalyzerForm(FlaskForm):
    """Form for analyzing potentially phishing links"""
    url = StringField('URL to Analyze', validators=[
        DataRequired(message='Please enter a URL to analyze'),
        Length(min=7, max=2048, message='URL must be between 7 and 2048 characters')
    ], render_kw={
        'placeholder': 'https://example.com or paste any suspicious link here...',
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent'
    })

    description = TextAreaField('Additional Context (Optional)', validators=[
        Optional(),
        Length(max=500, message='Description must be less than 500 characters')
    ], render_kw={
        'placeholder': 'Describe where you found this link or any suspicious behavior...',
        'rows': 3,
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent'
    })
