"""
Authentication views
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User
from app.views.auth.forms import LoginForm, RegistrationForm, ChangePasswordForm, ProfileUpdateForm
from app.utils.email_service import send_verification_email, send_welcome_email
from datetime import datetime

try:
    from app.utils.upload_service import upload_service
except ImportError:
    upload_service = None


auth = Blueprint('auth', __name__, url_prefix='/auth')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()

        if user and user.check_password(form.password.data):
            if user.account_status != 'active':
                flash('Your account is not active. Please contact support.', 'error')
                return render_template('auth/login.html', form=form)

            # Update last login
            user.last_login = datetime.now()
            db.session.commit()

            login_user(user, remember=form.remember_me.data)

            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('auth/login.html', form=form)


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter_by(email=form.email.data.lower()).first()
        if existing_user:
            flash('Email address already registered.', 'error')
            return render_template('auth/register.html', form=form)

        # Create new user
        user = User(
            email=form.email.data.lower(),
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone_number=form.phone_number.data,
            date_of_birth=form.date_of_birth.data,
            country=form.country.data,
            city=form.city.data,
            address=form.address.data,
            preferred_language=form.preferred_language.data,
            account_type=form.account_type.data,
            business_name=form.business_name.data,
            business_type=form.business_type.data,
            business_description=form.business_description.data,
            website_url=form.website_url.data
        )
        user.set_password(form.password.data)

        try:
            db.session.add(user)
            db.session.commit()

            # Send verification email
            send_verification_email(user)

            flash('Registration successful! A verification email has been sent to your email address.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Registration error: {e}")
            flash('An error occurred during registration. Please try again.', 'error')

    return render_template('auth/register.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password page"""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'error')
            return render_template('auth/change_password.html', form=form)

        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/change_password.html', form=form)


@auth.route('/admin')
@login_required
def admin():
    """Admin dashboard - redirect to new admin blueprint"""
    if not current_user.has_role('admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))

    # Redirect to new admin blueprint
    return redirect(url_for('admin.dashboard'))


@auth.route('/admin/users/<int:user_id>')
@login_required
def admin_user_detail(user_id):
    """Admin user detail page - redirect to new admin blueprint"""
    if not current_user.has_role('admin') and not current_user.can_access_user(user_id, 'read'):
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))

    # Redirect to new admin blueprint
    return redirect(url_for('admin.user_detail', user_id=user_id))


@auth.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile page"""
    form = ProfileUpdateForm()

    if form.validate_on_submit():
        # Update user data
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.phone_number = form.phone_number.data
        current_user.date_of_birth = form.date_of_birth.data
        current_user.country = form.country.data
        current_user.city = form.city.data
        current_user.address = form.address.data
        current_user.preferred_language = form.preferred_language.data
        current_user.business_name = form.business_name.data
        current_user.business_type = form.business_type.data
        current_user.business_description = form.business_description.data
        current_user.website_url = form.website_url.data

        # Handle profile image
        if form.remove_profile_image.data:
            # Remove current profile image
            if hasattr(current_user, 'delete_profile_image'):
                current_user.delete_profile_image()
            else:
                current_user.profile_image_url = None
                current_user.profile_thumbnail_url = None
        elif form.profile_image.data and upload_service:
            try:
                # Delete old image if exists
                if current_user.profile_image_url and hasattr(current_user, 'delete_profile_image'):
                    current_user.delete_profile_image()

                # Upload new image
                image_url = upload_service.upload_file(
                    form.profile_image.data,
                    folder='profiles',
                    create_thumbnail=True
                )
                if image_url:
                    thumbnail_url = upload_service.get_thumbnail_url(image_url)
                    if hasattr(current_user, 'set_profile_image'):
                        current_user.set_profile_image(image_url, thumbnail_url)
                    else:
                        current_user.profile_image_url = image_url
                        current_user.profile_thumbnail_url = thumbnail_url
            except Exception as e:
                current_app.logger.error(f"Profile image upload error: {e}")
                flash('Error uploading profile image. Profile updated without image.', 'warning')

        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Profile update error: {e}")
            flash('An error occurred while updating your profile.', 'error')

    # Pre-populate form with current user data
    elif request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.phone_number.data = current_user.phone_number
        form.date_of_birth.data = current_user.date_of_birth
        form.country.data = current_user.country
        form.city.data = current_user.city
        form.address.data = current_user.address
        form.preferred_language.data = current_user.preferred_language
        form.business_name.data = current_user.business_name
        form.business_type.data = current_user.business_type
        form.business_description.data = current_user.business_description
        form.website_url.data = current_user.website_url

    return render_template('auth/edit_profile.html', form=form)


@auth.route('/verify-email/<token>', methods=['GET', 'POST'])
def verify_email(token):
    """Verify email address"""

    if not current_user.is_authenticated:
        flash('You must be logged in to verify your email.', 'warning')
        return redirect(url_for('auth.login'))

    print(f"Verifying email with token: {token}")

    try:
        # Verify the token and get the user email
        email = current_user.verify_email_token(token)

        if not email:
            flash('Invalid or expired verification link.', 'error')
            return redirect(url_for('auth.login'))

        if current_user:
            current_user.account_status = 'active'
            db.session.commit()
            flash('Your email has been verified. You can now log in.', 'success')
        else:
            flash('User not found. Please register again.', 'error')
    except Exception as e:
        current_app.logger.error(f"Email verification error: {e}")
        flash('An error occurred during email verification. Please try again.', 'error')

    return redirect(url_for('auth.login'))


@auth.route('/resend-verification')
def resend_verification():
    """Resend verification email"""
    if current_user.is_authenticated:
        # Resend verification email
        send_verification_email(current_user)
        flash('Verification email resent. Please check your inbox.', 'info')
    else:
        flash('Please log in to resend the verification email.', 'warning')

    return redirect(url_for('auth.login'))


@auth.route('/welcome')
def welcome():
    """Welcome page after registration"""
    return render_template('auth/welcome.html')


@auth.route('forgot-password', methods=['GET', 'POST'])
def forgot_password():
    # TODO
    return "todo"
