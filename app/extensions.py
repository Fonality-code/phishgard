from flask_sqlalchemy import SQLAlchemy
from flask import request
from flask_babel import Babel
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_migrate import Migrate


def get_locale():
    language = request.accept_languages.best_match(['en','fr'])
    if not language:
        language = 'en'
    if current_user.is_authenticated and current_user.preferred_language:
        language = current_user.preferred_language
    return language

db = SQLAlchemy()
babel = Babel()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
mail = Mail()
migrate = Migrate()
