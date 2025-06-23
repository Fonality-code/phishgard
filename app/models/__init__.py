"""
Models package for PhishGuard application
"""
from app.models.user import User
from app.models.rbac import Role, Permission, UserRelationship, AccessControl
from app.models.simulation import (
    EmailTemplate, Employee, Campaign, CampaignTarget, CampaignEvent,
    TrainingModule, TrainingProgress, SimulationStatus, EmployeeStatus
)

__all__ = [
    'User', 'Role', 'Permission', 'UserRelationship', 'AccessControl',
    'EmailTemplate', 'Employee', 'Campaign', 'CampaignTarget', 'CampaignEvent',
    'TrainingModule', 'TrainingProgress', 'SimulationStatus', 'EmployeeStatus'
]
