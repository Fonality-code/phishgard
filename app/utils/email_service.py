"""
Email service utility for sending emails using Flask-Mail
"""
from flask import current_app, url_for, render_template
from flask_mail import Message
from app.extensions import mail
import threading


def send_async_email(app, msg):
    """Send email asynchronously"""
    with app.app_context():
        mail.send(msg)


def send_email(subject, recipients, text_body=None, html_body=None, sender=None):
    """
    Send email with optional async support

    Args:
        subject (str): Email subject
        recipients (list): List of recipient email addresses
        text_body (str): Plain text email body
        html_body (str): HTML email body
        sender (str): Sender email address (optional)
    """
    if sender is None:
        sender = current_app.config['MAIL_DEFAULT_SENDER']

    msg = Message(
        subject=subject,
        recipients=recipients,
        sender=sender
    )

    if text_body:
        msg.body = text_body
    if html_body:
        msg.html = html_body

    # Send email asynchronously if configured
    if current_app.config.get('MAIL_ASYNC', True):
        thr = threading.Thread(
            target=send_async_email,
            args=(current_app._get_current_object(), msg)
        )
        thr.start()
    else:
        mail.send(msg)


def send_verification_email(user):
    """
    Send email verification email to user

    Args:
        user: User object with email and verification token
    """
    token = user.generate_verification_token()

    verification_url = url_for(
        'auth.verify_email',
        token=token,
        _external=True
    )

    subject = f"[{current_app.config['APP_NAME']}] Please verify your email address"

    # Render email templates
    text_body = render_template(
        'emails/verify_email.txt',
        user=user,
        verification_url=verification_url
    )

    html_body = render_template(
        'emails/verify_email.html',
        user=user,
        verification_url=verification_url
    )

    send_email(
        subject=subject,
        recipients=[user.email],
        text_body=text_body,
        html_body=html_body
    )


def send_password_reset_email(user):
    """
    Send password reset email to user

    Args:
        user: User object with email
    """
    token = user.generate_reset_token()

    reset_url = url_for(
        'auth.reset_password',
        token=token,
        _external=True
    )

    subject = f"[{current_app.config['APP_NAME']}] Password Reset Request"

    # Render email templates
    text_body = render_template(
        'emails/reset_password.txt',
        user=user,
        reset_url=reset_url
    )

    html_body = render_template(
        'emails/reset_password.html',
        user=user,
        reset_url=reset_url
    )

    send_email(
        subject=subject,
        recipients=[user.email],
        text_body=text_body,
        html_body=html_body
    )


def send_welcome_email(user):
    """
    Send welcome email to newly registered user

    Args:
        user: User object
    """
    subject = f"Welcome to {current_app.config['APP_NAME']}!"

    # Render email templates
    text_body = render_template(
        'emails/welcome.txt',
        user=user
    )

    html_body = render_template(
        'emails/welcome.html',
        user=user
    )

    send_email(
        subject=subject,
        recipients=[user.email],
        text_body=text_body,
        html_body=html_body
    )


def send_account_notification(user, notification_type, **kwargs):
    """
    Send account-related notifications

    Args:
        user: User object
        notification_type: Type of notification ('login', 'profile_update', etc.)
        **kwargs: Additional template variables
    """
    notification_subjects = {
        'login': 'New login to your account',
        'profile_update': 'Profile updated successfully',
        'password_change': 'Password changed successfully',
        'email_change': 'Email address changed',
    }

    subject = f"[{current_app.config['APP_NAME']}] {notification_subjects.get(notification_type, 'Account notification')}"

    template_vars = {'user': user, **kwargs}

    # Render email templates
    text_body = render_template(
        f'emails/{notification_type}.txt',
        **template_vars
    )

    html_body = render_template(
        f'emails/{notification_type}.html',
        **template_vars
    )

    send_email(
        subject=subject,
        recipients=[user.email],
        text_body=text_body,
        html_body=html_body
    )
