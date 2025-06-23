"""
User model
"""
from datetime import datetime, timedelta
import secrets
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from typing import Any, List


class User(UserMixin, db.Model):
    """User model for authentication and user management"""

    __tablename__ = 'users'

    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Personal information
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)

    # Location information
    country = db.Column(db.String(2), nullable=False)  # ISO country code
    city = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=True)

    # Account settings
    preferred_language = db.Column(db.String(5), nullable=False, default='en')
    account_type = db.Column(db.String(20), nullable=False, default='customer')  # customer, business, both
    account_status = db.Column(db.String(20), nullable=False, default='active')  # active, inactive, banned
    email_verified = db.Column(db.Boolean, nullable=False, default=False)

    # Email verification
    email_verification_token = db.Column(db.String(255), nullable=True)
    email_verification_token_expires = db.Column(db.DateTime, nullable=True)

    # Business information (optional)
    business_name = db.Column(db.String(100), nullable=True)
    business_type = db.Column(db.String(50), nullable=True)
    business_description = db.Column(db.Text, nullable=True)
    website_url = db.Column(db.String(200), nullable=True)

    # Profile image
    profile_image_url = db.Column(db.String(500), nullable=True)
    profile_image_thumbnail_url = db.Column(db.String(500), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    last_login = db.Column(db.DateTime, nullable=True)

    # RBAC relationships
    from app.models.rbac import user_roles
    roles = db.relationship('Role',
                          secondary=user_roles,
                          backref=db.backref('users', lazy='dynamic'),
                          lazy='dynamic')

    def __repr__(self):
        return f'<User {self.email}>'

    def set_password(self, password: str):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"

    @property
    def is_business_user(self):
        """Check if user has business account type"""
        return self.account_type in ['business', 'both']

    @property
    def is_customer_user(self):
        """Check if user has customer account type"""
        return self.account_type in ['customer', 'both']

    def to_dict(self) -> dict[str, Any]:
        """Convert user to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'phone_number': self.phone_number,
            'country': self.country,
            'city': self.city,
            'preferred_language': self.preferred_language,
            'account_type': self.account_type,
            'account_status': self.account_status,
            'email_verified': self.email_verified,
            'business_name': self.business_name,
            'business_type': self.business_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

    # RBAC Methods
    def add_role(self, role):
        """Add role to user"""
        if not self.has_role(role.name):
            self.roles.append(role)

    def remove_role(self, role):
        """Remove role from user"""
        if self.has_role(role.name):
            self.roles.remove(role)

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role"""
        return self.roles.filter_by(name=role_name).first() is not None

    def has_permission(self, permission_name: str, resource_type: str = None, resource_id: int = None) -> bool:
        """Check if user has a specific permission"""
        # Check role-based permissions
        for role in self.roles:
            if role.has_permission(permission_name):
                return True

        # Check direct access control permissions
        from app.models.rbac import AccessControl, Permission
        query = AccessControl.query.join(Permission).filter(
            AccessControl.user_id == self.id,
            Permission.name == permission_name,
            AccessControl.is_granted == True
        )

        if resource_type:
            query = query.filter(AccessControl.resource_type == resource_type)

        if resource_id:
            query = query.filter(
                db.or_(
                    AccessControl.resource_id == resource_id,
                    AccessControl.resource_id.is_(None)
                )
            )

        # Check for non-expired permissions
        active_permissions = query.filter(
            db.or_(
                AccessControl.expires_at.is_(None),
                AccessControl.expires_at > datetime.now()
            )
        ).all()

        return len(active_permissions) > 0

    def can_access_user(self, target_user_id: int, permission_name: str) -> bool:
        """Check if user can access another user based on relationships"""
        if self.id == target_user_id:
            return True  # Users can always access themselves

        # Check if user has direct permission
        if self.has_permission(permission_name, 'user', target_user_id):
            return True

        # Check relationship-based access
        from app.models.rbac import UserRelationship
        relationships = UserRelationship.query.filter(
            UserRelationship.parent_user_id == self.id,
            UserRelationship.child_user_id == target_user_id,
            UserRelationship.is_active == True
        ).all()

        return len(relationships) > 0

    def get_accessible_users(self, permission_name: str = 'read') -> List[int]:
        """Get list of user IDs this user can access"""
        accessible_ids = [self.id]  # Always include self

        # Add users based on relationships
        from app.models.rbac import UserRelationship
        relationships = UserRelationship.query.filter(
            UserRelationship.parent_user_id == self.id,
            UserRelationship.is_active == True
        ).all()

        for rel in relationships:
            accessible_ids.append(rel.child_user_id)

        return accessible_ids

    # Profile Image Methods
    def get_profile_image(self, use_thumbnail: bool = False) -> str:
        """Get profile image URL, return default if none set"""
        if use_thumbnail and self.profile_image_thumbnail_url:
            return self.profile_image_thumbnail_url
        elif self.profile_image_url:
            return self.profile_image_url
        else:
            # Return default avatar based on initials
            return self.get_default_avatar_url()

    def get_default_avatar_url(self) -> str:
        """Generate default avatar URL based on user initials"""
        initials = f"{self.first_name[0]}{self.last_name[0]}" if self.first_name and self.last_name else "?"
        # Using a simple avatar service or can be replaced with local generation
        return f"https://ui-avatars.com/api/?name={initials}&background=3b82f6&color=ffffff&size=200"

    def set_profile_image(self, image_url: str, thumbnail_url: str = None):
        """Set profile image URLs"""
        self.profile_image_url = image_url
        self.profile_image_thumbnail_url = thumbnail_url

    def delete_profile_image(self):
        """Clear profile image URLs"""
        from app.utils.upload_service import upload_service

        # Delete files from storage
        if self.profile_image_url:
            upload_service.delete_file(self.profile_image_url)
        if self.profile_image_thumbnail_url:
            upload_service.delete_file(self.profile_image_thumbnail_url)

        # Clear URLs
        self.profile_image_url = None
        self.profile_image_thumbnail_url = None

    # Email Verification Methods
    def generate_verification_token(self) -> str:
        """Generate email verification token"""
        token = secrets.token_urlsafe(32)
        self.email_verification_token = token
        self.email_verification_token_expires = datetime.now() + timedelta(hours=24)
        
        db.session.commit()  # Save token to database
        return token

    def verify_email_token(self, token: str) -> bool:
        """Verify email verification token"""
        if not self.email_verification_token or not self.email_verification_token_expires:
            return False

        if datetime.now() > self.email_verification_token_expires:
            return False

        if self.email_verification_token == token:
            self.email_verified = True
            self.email_verification_token = None
            self.email_verification_token_expires = None
            return self.email

        return False

    def is_verification_token_expired(self) -> bool:
        """Check if verification token is expired"""
        if not self.email_verification_token_expires:
            return True
        return datetime.now() > self.email_verification_token_expires
