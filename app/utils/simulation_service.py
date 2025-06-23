"""
Phishing Simulation Service

This service handles the core logic for phishing simulations including:
- Campaign management
- Email sending
- Tracking and analytics
- Employee management
"""
import os
import uuid
from datetime import datetime, timedelta
from flask import current_app, url_for, render_template, request
from flask_mail import Message
from app.extensions import db, mail
from app.models.simulation import (
    Campaign, CampaignTarget, CampaignEvent, Employee, EmailTemplate,
    SimulationStatus, EmployeeStatus, TrainingModule, TrainingProgress
)
from app.utils.email_service import send_async_email
import threading
import logging

logger = logging.getLogger(__name__)


class PhishingSimulationService:
    """Service class for managing phishing simulations"""

    @staticmethod
    def create_campaign(name, description, email_template_id, created_by_id,
                       scheduled_start=None, employee_ids=None, **kwargs):
        """
        Create a new phishing campaign

        Args:
            name: Campaign name
            description: Campaign description
            email_template_id: ID of email template to use
            created_by_id: ID of user creating the campaign
            scheduled_start: When to start the campaign
            employee_ids: List of employee IDs to target
            **kwargs: Additional campaign settings

        Returns:
            Campaign object
        """
        campaign = Campaign(
            name=name,
            description=description,
            email_template_id=email_template_id,
            created_by_id=created_by_id,
            scheduled_start=scheduled_start,
            send_interval_minutes=kwargs.get('send_interval_minutes', 0),
            track_opens=kwargs.get('track_opens', True),
            track_clicks=kwargs.get('track_clicks', True),
            capture_credentials=kwargs.get('capture_credentials', False),
            organization_id=kwargs.get('organization_id')
        )

        db.session.add(campaign)
        db.session.flush()  # Get campaign ID

        # Add targets
        if employee_ids:
            for employee_id in employee_ids:
                target = CampaignTarget(
                    campaign_id=campaign.id,
                    employee_id=employee_id,
                    unique_id=str(uuid.uuid4())
                )
                db.session.add(target)

        db.session.commit()

        logger.info(f"Created campaign {campaign.id}: {name}")
        return campaign

    @staticmethod
    def start_campaign(campaign_id):
        """
        Start a phishing campaign

        Args:
            campaign_id: ID of campaign to start

        Returns:
            bool: Success status
        """
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return False

        if campaign.status != SimulationStatus.DRAFT:
            return False

        campaign.status = SimulationStatus.RUNNING
        campaign.actual_start = datetime.now()
        db.session.commit()

        # Send emails to targets
        PhishingSimulationService._send_campaign_emails(campaign)

        logger.info(f"Started campaign {campaign_id}")
        return True

    @staticmethod
    def _send_campaign_emails(campaign):
        """
        Send phishing emails for a campaign

        Args:
            campaign: Campaign object
        """
        template = campaign.email_template

        if campaign.send_interval_minutes > 0:
            # Schedule emails with intervals
            PhishingSimulationService._schedule_campaign_emails(campaign)
        else:
            # Send all emails immediately
            for target in campaign.targets:
                PhishingSimulationService._send_phishing_email(campaign, template, target)

    @staticmethod
    def _schedule_campaign_emails(campaign):
        """
        Schedule emails to be sent with intervals

        Args:
            campaign: Campaign object
        """
        # This would be implemented with a task queue like Celery in production
        # For now, we'll send them with threading delays
        def send_delayed_emails():
            template = campaign.email_template
            for i, target in enumerate(campaign.targets):
                if i > 0:
                    # Wait for the specified interval
                    import time
                    time.sleep(campaign.send_interval_minutes * 60)

                PhishingSimulationService._send_phishing_email(campaign, template, target)

        # Start background thread
        thread = threading.Thread(target=send_delayed_emails)
        thread.daemon = True
        thread.start()

    @staticmethod
    def _send_phishing_email(campaign, template, target):
        """
        Send a single phishing email

        Args:
            campaign: Campaign object
            template: EmailTemplate object
            target: CampaignTarget object
        """
        try:
            # Generate tracking URLs
            tracking_pixel_url = url_for(
                'simulation.track_open',
                target_id=target.unique_id,
                _external=True
            )

            phishing_link_url = url_for(
                'simulation.track_click',
                target_id=target.unique_id,
                _external=True
            )

            # Personalize email content
            html_content = template.html_content
            text_content = template.text_content or ""

            # Replace placeholders
            replacements = {
                '{{first_name}}': target.employee.first_name,
                '{{last_name}}': target.employee.last_name,
                '{{full_name}}': target.employee.full_name,
                '{{email}}': target.employee.email,
                '{{department}}': target.employee.department or '',
                '{{position}}': target.employee.position or '',
                '{{tracking_pixel}}': f'<img src="{tracking_pixel_url}" width="1" height="1" style="display:none;" />',
                '{{phishing_link}}': phishing_link_url
            }

            for placeholder, value in replacements.items():
                html_content = html_content.replace(placeholder, value)
                text_content = text_content.replace(placeholder, value)

            # Create email message
            msg = Message(
                subject=template.subject,
                recipients=[target.employee.email],
                sender=(template.sender_name, template.sender_email),
                html=html_content,
                body=text_content
            )

            # Send email asynchronously
            app = current_app._get_current_object()
            thread = threading.Thread(
                target=send_async_email,
                args=(app, msg)
            )
            thread.start()

            # Mark as sent
            target.mark_as_sent()

            # Log event
            PhishingSimulationService._log_campaign_event(
                campaign.id,
                target.id,
                'email_sent',
                {'template_id': template.id}
            )

            logger.info(f"Sent phishing email to {target.employee.email} for campaign {campaign.id}")

        except Exception as e:
            logger.error(f"Failed to send phishing email to {target.employee.email}: {str(e)}")
            target.status = EmployeeStatus.FAILED
            db.session.commit()

    @staticmethod
    def track_email_open(target_id, ip_address=None, user_agent=None):
        """
        Track when a phishing email is opened

        Args:
            target_id: Unique target ID
            ip_address: IP address of the opener
            user_agent: User agent string

        Returns:
            bool: Success status
        """
        target = CampaignTarget.query.filter_by(unique_id=target_id).first()
        if not target:
            return False

        target.mark_as_opened(ip_address, user_agent)

        # Log event
        PhishingSimulationService._log_campaign_event(
            target.campaign_id,
            target.id,
            'email_opened',
            {'ip_address': ip_address, 'user_agent': user_agent}
        )

        logger.info(f"Email opened by target {target_id}")
        return True

    @staticmethod
    def track_link_click(target_id, ip_address=None, user_agent=None):
        """
        Track when a phishing link is clicked

        Args:
            target_id: Unique target ID
            ip_address: IP address of the clicker
            user_agent: User agent string

        Returns:
            tuple: (success, landing_page_url)
        """
        target = CampaignTarget.query.filter_by(unique_id=target_id).first()
        if not target:
            return False, None

        target.mark_as_clicked(ip_address, user_agent)

        # Log event
        PhishingSimulationService._log_campaign_event(
            target.campaign_id,
            target.id,
            'link_clicked',
            {'ip_address': ip_address, 'user_agent': user_agent}
        )

        # Get landing page URL
        template = target.campaign.email_template
        landing_page_url = template.landing_page_url or url_for(
            'simulation.phishing_awareness',
            _external=True
        )

        logger.info(f"Link clicked by target {target_id}")
        return True, landing_page_url

    @staticmethod
    def report_phishing_email(target_id):
        """
        Mark an email as reported by the employee

        Args:
            target_id: Unique target ID

        Returns:
            bool: Success status
        """
        target = CampaignTarget.query.filter_by(unique_id=target_id).first()
        if not target:
            return False

        target.mark_as_reported()

        # Log event
        PhishingSimulationService._log_campaign_event(
            target.campaign_id,
            target.id,
            'email_reported',
            {}
        )

        logger.info(f"Email reported by target {target_id}")
        return True

    @staticmethod
    def _log_campaign_event(campaign_id, target_id, event_type, event_data):
        """
        Log a campaign event

        Args:
            campaign_id: Campaign ID
            target_id: Target ID (optional)
            event_type: Type of event
            event_data: Additional event data
        """
        event = CampaignEvent(
            campaign_id=campaign_id,
            target_id=target_id,
            event_type=event_type,
            event_data=event_data,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None
        )

        db.session.add(event)
        db.session.commit()

    @staticmethod
    def get_campaign_analytics(campaign_id):
        """
        Get comprehensive analytics for a campaign

        Args:
            campaign_id: Campaign ID

        Returns:
            dict: Analytics data
        """
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return None

        # Basic stats
        stats = {
            'campaign': campaign.to_dict(),
            'total_targets': campaign.total_targets,
            'emails_sent': campaign.emails_sent,
            'emails_opened': campaign.emails_opened,
            'links_clicked': campaign.links_clicked,
            'emails_reported': campaign.emails_reported,
            'success_rate': campaign.success_rate,
            'awareness_rate': campaign.awareness_rate
        }

        # Timeline data
        events = db.session.query(CampaignEvent).filter_by(campaign_id=campaign_id).order_by(CampaignEvent.timestamp).all()
        timeline = events  # Pass events directly instead of converting to dict

        # Department breakdown
        department_stats = {}
        for target in campaign.targets:
            dept = target.employee.department or 'Unknown'
            if dept not in department_stats:
                department_stats[dept] = {
                    'total': 0,
                    'sent': 0,
                    'opened': 0,
                    'clicked': 0,
                    'reported': 0
                }

            department_stats[dept]['total'] += 1
            if target.status != EmployeeStatus.PENDING:
                department_stats[dept]['sent'] += 1
            if target.status in [EmployeeStatus.OPENED, EmployeeStatus.CLICKED, EmployeeStatus.REPORTED]:
                department_stats[dept]['opened'] += 1
            if target.status in [EmployeeStatus.CLICKED, EmployeeStatus.REPORTED]:
                department_stats[dept]['clicked'] += 1
            if target.status == EmployeeStatus.REPORTED:
                department_stats[dept]['reported'] += 1

        stats['timeline'] = timeline
        stats['department_breakdown'] = department_stats

        return stats

    @staticmethod
    def create_employee(email, first_name, last_name, department=None,
                       position=None, employee_id=None, created_by_id=None, organization_id=None):
        """
        Create a new employee record

        Args:
            email: Employee email
            first_name: Employee first name
            last_name: Employee last name
            department: Employee department
            position: Employee position
            employee_id: External employee ID
            created_by_id: ID of user creating the record
            organization_id: Organization ID

        Returns:
            Employee object
        """
        employee = Employee(
            email=email,
            first_name=first_name,
            last_name=last_name,
            department=department,
            position=position,
            employee_id=employee_id,
            created_by_id=created_by_id,
            organization_id=organization_id
        )

        db.session.add(employee)
        db.session.commit()

        logger.info(f"Created employee record for {email}")
        return employee

    @staticmethod
    def bulk_import_employees(employee_data, created_by_id, organization_id=None):
        """
        Bulk import employees from a list

        Args:
            employee_data: List of employee dictionaries
            created_by_id: ID of user creating the records
            organization_id: Organization ID

        Returns:
            tuple: (success_count, error_count, errors)
        """
        success_count = 0
        error_count = 0
        errors = []

        for data in employee_data:
            try:
                # Check if employee already exists
                existing = Employee.query.filter_by(
                    email=data.get('email'),
                    organization_id=organization_id
                ).first()

                if existing:
                    errors.append(f"Employee {data.get('email')} already exists")
                    error_count += 1
                    continue

                employee = PhishingSimulationService.create_employee(
                    email=data.get('email'),
                    first_name=data.get('first_name'),
                    last_name=data.get('last_name'),
                    department=data.get('department'),
                    position=data.get('position'),
                    employee_id=data.get('employee_id'),
                    created_by_id=created_by_id,
                    organization_id=organization_id
                )
                success_count += 1

            except Exception as e:
                errors.append(f"Error importing {data.get('email', 'unknown')}: {str(e)}")
                error_count += 1

        logger.info(f"Bulk import completed: {success_count} success, {error_count} errors")
        return success_count, error_count, errors

    @staticmethod
    def pause_campaign(campaign_id):
        """
        Pause a running campaign

        Args:
            campaign_id: Campaign ID

        Returns:
            bool: Success status
        """
        campaign = Campaign.query.get(campaign_id)
        if not campaign or campaign.status != SimulationStatus.RUNNING:
            return False

        campaign.status = SimulationStatus.PAUSED
        db.session.commit()

        logger.info(f"Paused campaign {campaign_id}")
        return True

    @staticmethod
    def resume_campaign(campaign_id):
        """
        Resume a paused campaign

        Args:
            campaign_id: Campaign ID

        Returns:
            bool: Success status
        """
        campaign = Campaign.query.get(campaign_id)
        if not campaign or campaign.status != SimulationStatus.PAUSED:
            return False

        campaign.status = SimulationStatus.RUNNING
        db.session.commit()

        logger.info(f"Resumed campaign {campaign_id}")
        return True

    @staticmethod
    def complete_campaign(campaign_id):
        """
        Mark a campaign as completed

        Args:
            campaign_id: Campaign ID

        Returns:
            bool: Success status
        """
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return False

        campaign.status = SimulationStatus.COMPLETED
        campaign.actual_end = datetime.now()
        db.session.commit()

        logger.info(f"Completed campaign {campaign_id}")
        return True

    @staticmethod
    def get_organization_dashboard_stats(organization_id=None, created_by_id=None):
        """
        Get dashboard statistics for an organization or user

        Args:
            organization_id: Organization ID
            created_by_id: User ID (if not organization-wide)

        Returns:
            dict: Dashboard statistics
        """
        # Base query filters
        campaign_filter = {}
        if organization_id:
            campaign_filter['organization_id'] = organization_id
        elif created_by_id:
            campaign_filter['created_by_id'] = created_by_id

        # Total campaigns
        total_campaigns = Campaign.query.filter_by(**campaign_filter).count()

        # Active campaigns
        active_campaigns = Campaign.query.filter_by(
            **campaign_filter,
            status=SimulationStatus.RUNNING
        ).count()

        # Completed campaigns
        completed_campaigns = Campaign.query.filter_by(
            **campaign_filter,
            status=SimulationStatus.COMPLETED
        ).count()

        # Total employees
        employee_filter = {}
        if organization_id:
            employee_filter['organization_id'] = organization_id
        elif created_by_id:
            employee_filter['created_by_id'] = created_by_id

        total_employees = Employee.query.filter_by(**employee_filter).count()

        # This month's campaigns
        this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month_campaigns = Campaign.query.filter(
            Campaign.created_at >= this_month_start
        ).filter_by(**campaign_filter).count()

        # High risk employees (clicked phishing links recently)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        high_risk_employees = db.session.query(Employee.id).join(
            CampaignTarget
        ).filter(
            CampaignTarget.status == EmployeeStatus.CLICKED,
            CampaignTarget.clicked_at >= thirty_days_ago
        ).distinct().count()

        return {
            'total_campaigns': total_campaigns,
            'active_campaigns': active_campaigns,
            'completed_campaigns': completed_campaigns,
            'total_employees': total_employees,
            'this_month_campaigns': this_month_campaigns,
            'high_risk_employees': high_risk_employees
        }
