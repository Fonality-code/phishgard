from flask import Blueprint, render_template
from flask_login import current_user


main = Blueprint('main', __name__)


@main.route('/')
def index():
    dashboard_stats = None
    if current_user.is_authenticated:
        from app.utils.simulation_service import PhishingSimulationService
        dashboard_stats = PhishingSimulationService.get_organization_dashboard_stats(
            created_by_id=current_user.id
        )

    return render_template('main/index.html', dashboard_stats=dashboard_stats)
