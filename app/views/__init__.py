from flask import Flask
from .main import main as main_blueprint
from .auth import auth as auth_blueprint
from .admin import admin as admin_blueprint
from .simulation import simulation as simulation_blueprint


def register_blueprints(app: Flask):
    """Register all blueprints for the application."""
    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(admin_blueprint)
    app.register_blueprint(simulation_blueprint)
