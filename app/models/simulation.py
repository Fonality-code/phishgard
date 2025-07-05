"""
Phishing Simulation Models

This module contains all models related to phishing simulations, campaigns,
email templates, employees, and analytics.
"""
from datetime import datetime, timedelta
from enum import Enum
import secrets
import uuid
from flask import url_for
from app.extensions import db
from app.models.user import User


class SimulationStatus(Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class EmployeeStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    OPENED = "opened"
    CLICKED = "clicked"
    REPORTED = "reported"
    FAILED = "failed"


class EmailTemplate(db.Model):
    """Email templates for phishing simulations"""

    __tablename__ = 'email_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)  # social_engineering, urgent, finance, etc.
    difficulty_level = db.Column(db.String(20), nullable=False, default='medium')  # easy, medium, hard

    # Email content
    subject = db.Column(db.String(200), nullable=False)
    sender_name = db.Column(db.String(100), nullable=False)
    sender_email = db.Column(db.String(100), nullable=False)
    html_content = db.Column(db.Text, nullable=False)
    text_content = db.Column(db.Text, nullable=True)

    # Landing page for clicked links
    landing_page_url = db.Column(db.String(500), nullable=True)
    landing_page_content = db.Column(db.Text, nullable=True)

    # Template metadata
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_system_template = db.Column(db.Boolean, nullable=False, default=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    organization_id = db.Column(db.Integer, nullable=True)  # For multi-tenant support

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # Relationships
    created_by = db.relationship('User', backref='email_templates')
    campaigns = db.relationship('Campaign', backref='email_template')

    def __repr__(self):
        return f'<EmailTemplate {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'difficulty_level': self.difficulty_level,
            'subject': self.subject,
            'sender_name': self.sender_name,
            'sender_email': self.sender_email,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Employee(db.Model):
    """Employee records for phishing simulations"""

    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), nullable=True)  # External employee ID
    email = db.Column(db.String(120), nullable=False, index=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100), nullable=True)
    position = db.Column(db.String(100), nullable=True)

    # Status and metadata
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    organization_id = db.Column(db.Integer, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # Relationships
    created_by = db.relationship('User', backref='employees')
    campaign_targets = db.relationship('CampaignTarget', backref='employee')

    def __repr__(self):
        return f'<Employee {self.email}>'

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'department': self.department,
            'position': self.position,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Campaign(db.Model):
    """Phishing simulation campaigns"""

    __tablename__ = 'campaigns'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Campaign settings
    email_template_id = db.Column(db.Integer, db.ForeignKey('email_templates.id'), nullable=False)
    status = db.Column(db.Enum(SimulationStatus), nullable=False, default=SimulationStatus.DRAFT)

    # Scheduling
    scheduled_start = db.Column(db.DateTime, nullable=True)
    scheduled_end = db.Column(db.DateTime, nullable=True)
    actual_start = db.Column(db.DateTime, nullable=True)
    actual_end = db.Column(db.DateTime, nullable=True)

    # Campaign settings
    send_interval_minutes = db.Column(db.Integer, nullable=False, default=0)  # 0 = send all at once
    track_opens = db.Column(db.Boolean, nullable=False, default=True)
    track_clicks = db.Column(db.Boolean, nullable=False, default=True)
    capture_credentials = db.Column(db.Boolean, nullable=False, default=False)

    # Metadata
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    organization_id = db.Column(db.Integer, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # Relationships
    created_by = db.relationship('User', backref='campaigns')
    targets = db.relationship('CampaignTarget', backref='campaign', cascade='all, delete-orphan')
    events = db.relationship('CampaignEvent', backref='campaign', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Campaign {self.name}>'

    @property
    def total_targets(self):
        return len(self.targets)

    @property
    def emails_sent(self):
        return sum(1 for target in self.targets if target.status != EmployeeStatus.PENDING)

    @property
    def emails_opened(self):
        return sum(1 for target in self.targets if target.status in [EmployeeStatus.OPENED, EmployeeStatus.CLICKED, EmployeeStatus.REPORTED])

    @property
    def links_clicked(self):
        return sum(1 for target in self.targets if target.status in [EmployeeStatus.CLICKED, EmployeeStatus.REPORTED])

    @property
    def emails_reported(self):
        return sum(1 for target in self.targets if target.status == EmployeeStatus.REPORTED)

    @property
    def success_rate(self):
        """Percentage of employees who clicked the phishing link"""
        if self.emails_sent == 0:
            return 0
        return (self.links_clicked / self.emails_sent) * 100

    @property
    def awareness_rate(self):
        """Percentage of employees who reported the phishing email"""
        if self.emails_sent == 0:
            return 0
        return (self.emails_reported / self.emails_sent) * 100

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'scheduled_start': self.scheduled_start.isoformat() if self.scheduled_start else None,
            'scheduled_end': self.scheduled_end.isoformat() if self.scheduled_end else None,
            'actual_start': self.actual_start.isoformat() if self.actual_start else None,
            'actual_end': self.actual_end.isoformat() if self.actual_end else None,
            'total_targets': self.total_targets,
            'emails_sent': self.emails_sent,
            'emails_opened': self.emails_opened,
            'links_clicked': self.links_clicked,
            'emails_reported': self.emails_reported,
            'success_rate': self.success_rate,
            'awareness_rate': self.awareness_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CampaignTarget(db.Model):
    """Individual targets within a campaign"""

    __tablename__ = 'campaign_targets'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)

    # Tracking
    unique_id = db.Column(db.String(50), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    status = db.Column(db.Enum(EmployeeStatus), nullable=False, default=EmployeeStatus.PENDING)

    # Email delivery
    sent_at = db.Column(db.DateTime, nullable=True)
    opened_at = db.Column(db.DateTime, nullable=True)
    clicked_at = db.Column(db.DateTime, nullable=True)
    reported_at = db.Column(db.DateTime, nullable=True)

    # Tracking data
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    click_count = db.Column(db.Integer, nullable=False, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f'<CampaignTarget {self.unique_id}>'

    def mark_as_sent(self):
        """Mark email as sent"""
        self.status = EmployeeStatus.SENT
        self.sent_at = datetime.now()
        db.session.commit()

    def mark_as_opened(self, ip_address=None, user_agent=None):
        """Mark email as opened"""
        if self.status == EmployeeStatus.SENT:
            self.status = EmployeeStatus.OPENED
            self.opened_at = datetime.now()
            if ip_address:
                self.ip_address = ip_address
            if user_agent:
                self.user_agent = user_agent
            db.session.commit()

    def mark_as_clicked(self, ip_address=None, user_agent=None):
        """Mark link as clicked"""
        self.status = EmployeeStatus.CLICKED
        self.clicked_at = datetime.now()
        self.click_count += 1
        if ip_address:
            self.ip_address = ip_address
        if user_agent:
            self.user_agent = user_agent
        db.session.commit()

    def mark_as_reported(self):
        """Mark email as reported"""
        self.status = EmployeeStatus.REPORTED
        self.reported_at = datetime.now()
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'unique_id': self.unique_id,
            'status': self.status.value,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'clicked_at': self.clicked_at.isoformat() if self.clicked_at else None,
            'reported_at': self.reported_at.isoformat() if self.reported_at else None,
            'click_count': self.click_count,
            'employee': self.employee.to_dict() if self.employee else None
        }


class CampaignEvent(db.Model):
    """Event log for campaign activities"""

    __tablename__ = 'campaign_events'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('campaign_targets.id'), nullable=True)

    event_type = db.Column(db.String(50), nullable=False)  # email_sent, email_opened, link_clicked, etc.
    event_data = db.Column(db.JSON, nullable=True)  # Additional event-specific data
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)

    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)

    # Relationships
    target = db.relationship('CampaignTarget', backref='events')

    def __repr__(self):
        return f'<CampaignEvent {self.event_type}>'

    def to_dict(self):
        return {
            'id': self.id,
            'event_type': self.event_type,
            'event_data': self.event_data,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat()
        }


class TrainingModule(db.Model):
    """Training modules for cybersecurity education"""

    __tablename__ = 'training_modules'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=False)

    # Module settings
    category = db.Column(db.String(50), nullable=False)
    difficulty_level = db.Column(db.String(20), nullable=False, default='beginner')
    estimated_duration = db.Column(db.Integer, nullable=False, default=10)  # minutes

    # Content
    video_url = db.Column(db.String(500), nullable=True)
    quiz_questions = db.Column(db.JSON, nullable=True)

    # Metadata
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    organization_id = db.Column(db.Integer, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # Relationships
    created_by = db.relationship('User', backref='training_modules')
    progress_records = db.relationship('TrainingProgress', backref='training_module')

    def __repr__(self):
        return f'<TrainingModule {self.title}>'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'difficulty_level': self.difficulty_level,
            'estimated_duration': self.estimated_duration,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TrainingProgress(db.Model):
    """Track employee progress through training modules"""

    __tablename__ = 'training_progress'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    training_module_id = db.Column(db.Integer, db.ForeignKey('training_modules.id'), nullable=False)

    # Progress tracking
    status = db.Column(db.String(20), nullable=False, default='not_started')  # not_started, in_progress, completed
    progress_percentage = db.Column(db.Integer, nullable=False, default=0)
    time_spent = db.Column(db.Integer, nullable=False, default=0)  # minutes

    # Quiz results
    quiz_score = db.Column(db.Integer, nullable=True)  # percentage
    quiz_attempts = db.Column(db.Integer, nullable=False, default=0)

    # Timestamps
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    last_accessed = db.Column(db.DateTime, nullable=True)

    # Relationships
    employee = db.relationship('Employee', backref='training_progress')

    def __repr__(self):
        return f'<TrainingProgress {self.employee.email} - {self.training_module.title}>'

    def to_dict(self):
        return {
            'id': self.id,
            'status': self.status,
            'progress_percentage': self.progress_percentage,
            'time_spent': self.time_spent,
            'quiz_score': self.quiz_score,
            'quiz_attempts': self.quiz_attempts,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None
        }


class AISecurityChat(db.Model):
    """AI-powered security chat sessions for phishing awareness"""

    __tablename__ = 'ai_security_chats'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))

    # Connection to phishing simulation
    target_id = db.Column(db.String(64), nullable=True)  # CampaignTarget unique_id
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # If user is logged in

    # Session metadata
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)

    # Session tracking
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    last_activity = db.Column(db.DateTime, nullable=False, default=datetime.now)
    ended_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Relationships
    user = db.relationship('User', backref='ai_chat_sessions')
    messages = db.relationship('AIChatMessage', backref='chat_session', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<AISecurityChat {self.session_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'target_id': self.target_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'is_active': self.is_active,
            'message_count': len(self.messages)
        }


class AIChatMessage(db.Model):
    """Individual messages in AI security chat sessions"""

    __tablename__ = 'ai_chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    chat_session_id = db.Column(db.Integer, db.ForeignKey('ai_security_chats.id'), nullable=False)

    # Message content
    message = db.Column(db.Text, nullable=False)
    is_user = db.Column(db.Boolean, nullable=False)  # True for user messages, False for AI responses

    # AI metadata (for AI messages only)
    ai_model = db.Column(db.String(50), nullable=True)  # e.g., 'gpt-4', 'claude-3'
    response_time_ms = db.Column(db.Integer, nullable=True)  # AI response time in milliseconds

    # Timestamps
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        sender = "User" if self.is_user else "AI"
        return f'<AIChatMessage {sender}: {self.message[:50]}...>'

    def to_dict(self):
        return {
            'id': self.id,
            'message': self.message,
            'is_user': self.is_user,
            'ai_model': self.ai_model,
            'response_time_ms': self.response_time_ms,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
