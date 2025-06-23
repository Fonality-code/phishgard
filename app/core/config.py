import os

class Config:
    """
    Configuration class for the application.
    """

    SECRET_KEY: str = os.getenv('SECRET_KEY', 'default_secret_key')
    SQLALCHEMY_DATABASE_URI: str = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')

    # BABEL_DEFAULT_LOCALE: str = os.getenv('BABEL_DEFAULT_LOCALE', 'en')

    # Email Configuration
    MAIL_SERVER: str = os.getenv('MAIL_SERVER', 'sandbox.smtp.mailtrap.io')
    MAIL_PORT: int = int(os.getenv('MAIL_PORT', '2525'))
    MAIL_USE_TLS: bool = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    MAIL_USE_SSL: bool = os.getenv('MAIL_USE_SSL', 'False').lower() in ('true', '1', 't')
    MAIL_USERNAME: str = os.getenv('MAIL_USERNAME', 'e70f7ebba1121a')
    MAIL_PASSWORD: str = os.getenv('MAIL_PASSWORD', 'c7d89790dc29b7')
    MAIL_DEFAULT_SENDER: str = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@webapp.com')

    # Application settings

    APPLICATION_NAME: str = os.getenv('APPLICATION_NAME', 'Web App')
    APP_NAME = APPLICATION_NAME
    FRONTEND_URL: str = os.getenv('FRONTEND_URL', 'http://localhost:5000')
