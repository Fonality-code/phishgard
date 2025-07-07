"""
Simulation Blueprint Views

This module contains all views related to phishing simulations including:
- Campaign management
- Email tracking
- Analytics dashboard
- Employee management
"""
from flask_babel import _
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import csv
import io
import logging
from app.extensions import db
from app.models.simulation import (
    Campaign, CampaignTarget, Employee, EmailTemplate,
    SimulationStatus, EmployeeStatus, TrainingModule, TrainingProgress
)
from app.utils.simulation_service import PhishingSimulationService
from .forms import (
    CampaignForm, EmployeeForm, EmailTemplateForm, BulkEmployeeUploadForm
)

simulation = Blueprint('simulation', __name__, url_prefix='/simulation')

logger = logging.getLogger(__name__)


@simulation.route('/')
@login_required
def dashboard():
    """Simulation dashboard with overview stats"""
    # Get dashboard statistics
    stats = PhishingSimulationService.get_organization_dashboard_stats(
        created_by_id=current_user.id
    )

    # Get recent campaigns
    recent_campaigns = Campaign.query.filter_by(
        created_by_id=current_user.id
    ).order_by(Campaign.created_at.desc()).limit(5).all()

    # Get active campaigns
    active_campaigns = Campaign.query.filter_by(
        created_by_id=current_user.id,
        status=SimulationStatus.RUNNING
    ).all()

    return render_template('simulation/dashboard.html',
                         stats=stats,
                         recent_campaigns=recent_campaigns,
                         active_campaigns=active_campaigns)


@simulation.route('/campaigns')
@login_required
def campaigns():
    """List all campaigns"""
    page = request.args.get('page', 1, type=int)
    campaigns = Campaign.query.filter_by(
        created_by_id=current_user.id
    ).order_by(Campaign.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template('simulation/campaigns.html', campaigns=campaigns)


@simulation.route('/campaigns/create', methods=['GET', 'POST'])
@login_required
def create_campaign():
    """Create a new campaign"""
    form = CampaignForm()

    # Populate form choices
    form.email_template_id.choices = [
        (t.id, f"{t.name} ({t.category})")
        for t in EmailTemplate.query.filter_by(
            created_by_id=current_user.id, is_active=True
        ).all()
    ]

    employees = Employee.query.filter_by(
        created_by_id=current_user.id, is_active=True
    ).all()
    form.employee_ids.choices = [
        (e.id, f"{e.full_name} ({e.email})")
        for e in employees
    ]

    if form.validate_on_submit():
        try:
            campaign = PhishingSimulationService.create_campaign(
                name=form.name.data,
                description=form.description.data,
                email_template_id=form.email_template_id.data,
                created_by_id=current_user.id,
                scheduled_start=form.scheduled_start.data,
                employee_ids=form.employee_ids.data,
                send_interval_minutes=form.send_interval_minutes.data,
                track_opens=form.track_opens.data,
                track_clicks=form.track_clicks.data
            )

            flash('Campaign created successfully!', 'success')
            return redirect(url_for('simulation.campaign_detail', id=campaign.id))

        except Exception as e:
            flash(f'Error creating campaign: {str(e)}', 'error')

    return render_template('simulation/create_campaign.html', form=form)


@simulation.route('/campaigns/<int:id>')
@login_required
def campaign_detail(id):
    """Campaign detail view with analytics"""
    campaign = Campaign.query.get_or_404(id)

    # Check permission
    if campaign.created_by_id != current_user.id:
        abort(403)

    # Get analytics
    analytics = PhishingSimulationService.get_campaign_analytics(id)

    # Get available training modules for assignment
    training_modules_objects = TrainingModule.query.filter_by(
        is_active=True,
        created_by_id=current_user.id
    ).order_by(TrainingModule.title).all()

    # Convert to dictionaries for JSON serialization
    training_modules = [module.to_dict() for module in training_modules_objects]

    # Get employees who clicked the phishing link (failed the test)
    failed_employees = []
    for target in campaign.targets:
        if target.status in [EmployeeStatus.CLICKED]:
            failed_employees.append(target.employee)

    return render_template('simulation/campaign_detail.html',
                         campaign=campaign,
                         analytics=analytics,
                         training_modules=training_modules,
                         failed_employees=failed_employees)


@simulation.route('/campaigns/<int:id>/start', methods=['POST'])
@login_required
def start_campaign(id):
    """Start a campaign"""
    campaign = Campaign.query.get_or_404(id)

    if campaign.created_by_id != current_user.id:
        abort(403)

    success = PhishingSimulationService.start_campaign(id)

    if success:
        flash('Campaign started successfully!', 'success')
    else:
        flash('Failed to start campaign. Check campaign status.', 'error')

    return redirect(url_for('simulation.campaign_detail', id=id))


@simulation.route('/campaigns/<int:id>/pause', methods=['POST'])
@login_required
def pause_campaign(id):
    """Pause a campaign"""
    campaign = Campaign.query.get_or_404(id)

    if campaign.created_by_id != current_user.id:
        abort(403)

    success = PhishingSimulationService.pause_campaign(id)

    if success:
        flash('Campaign paused successfully!', 'success')
    else:
        flash('Failed to pause campaign.', 'error')

    return redirect(url_for('simulation.campaign_detail', id=id))


@simulation.route('/campaigns/<int:id>/complete', methods=['POST'])
@login_required
def complete_campaign(id):
    """Complete a campaign"""
    campaign = Campaign.query.get_or_404(id)

    if campaign.created_by_id != current_user.id:
        abort(403)

    success = PhishingSimulationService.complete_campaign(id)

    if success:
        flash('Campaign completed successfully!', 'success')
    else:
        flash('Failed to complete campaign.', 'error')

    return redirect(url_for('simulation.campaign_detail', id=id))


@simulation.route('/campaigns/<int:id>/assign-training', methods=['POST'])
@login_required
def assign_training_to_campaign(id):
    """Assign training module to employees who failed the campaign"""
    campaign = Campaign.query.get_or_404(id)

    if campaign.created_by_id != current_user.id:
        abort(403)

    try:
        data = request.get_json()
        training_module_id = data.get('training_module_id')
        assignment_type = data.get('assignment_type', 'failed_only')  # failed_only, all_targets
        due_date = datetime.fromisoformat(data.get('due_date')) if data.get('due_date') else None

        if not training_module_id:
            return jsonify({'success': False, 'error': 'Training module ID is required'})

        # Get the training module
        training_module = TrainingModule.query.get_or_404(training_module_id)

        if training_module.created_by_id != current_user.id:
            return jsonify({'success': False, 'error': 'Training module not found'})

        assigned_count = 0
        employees_to_assign = []

        if assignment_type == 'failed_only':
            # Assign only to employees who clicked the phishing link
            for target in campaign.targets:
                if target.status in [EmployeeStatus.CLICKED]:
                    employees_to_assign.append(target.employee)
        elif assignment_type == 'all_targets':
            # Assign to all campaign targets
            employees_to_assign = [target.employee for target in campaign.targets]
        else:
            return jsonify({'success': False, 'error': 'Invalid assignment type'})

        # Create training progress records
        for employee in employees_to_assign:
            existing = TrainingProgress.query.filter_by(
                employee_id=employee.id,
                training_module_id=training_module_id
            ).first()

            if not existing:
                progress = TrainingProgress(
                    employee_id=employee.id,
                    training_module_id=training_module_id,
                    started_at=datetime.utcnow(),
                    status='not_started'
                )
                db.session.add(progress)
                assigned_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'assigned_count': assigned_count,
            'training_module': training_module.title
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@simulation.route('/employees')
@login_required
def employees():
    """List all employees"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')

    query = Employee.query.filter_by(created_by_id=current_user.id)

    if search:
        query = query.filter(
            db.or_(
                Employee.email.contains(search),
                Employee.first_name.contains(search),
                Employee.last_name.contains(search),
                Employee.department.contains(search)
            )
        )

    employees = query.order_by(Employee.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template('simulation/employees.html',
                         employees=employees, search=search)


@simulation.route('/employees/create', methods=['GET', 'POST'])
@login_required
def create_employee():
    """Create a new employee"""
    form = EmployeeForm()

    if form.validate_on_submit():
        try:
            employee = PhishingSimulationService.create_employee(
                email=form.email.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                department=form.department.data,
                position=form.position.data,
                employee_id=form.employee_id.data,
                created_by_id=current_user.id
            )

            flash('Employee created successfully!', 'success')
            return redirect(url_for('simulation.employees'))

        except Exception as e:
            flash(f'Error creating employee: {str(e)}', 'error')

    return render_template('simulation/create_employee.html', form=form)


@simulation.route('/employees/bulk-upload', methods=['GET', 'POST'])
@login_required
def bulk_upload_employees():
    """Bulk upload employees from CSV"""
    form = BulkEmployeeUploadForm()

    if form.validate_on_submit():
        try:
            # Read CSV file
            csv_file = form.csv_file.data
            csv_content = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_content))

            # Convert to list of dicts
            employee_data = []
            for row in csv_reader:
                employee_data.append({
                    'email': row.get('email', '').strip(),
                    'first_name': row.get('first_name', '').strip(),
                    'last_name': row.get('last_name', '').strip(),
                    'department': row.get('department', '').strip(),
                    'position': row.get('position', '').strip(),
                    'employee_id': row.get('employee_id', '').strip()
                })

            # Bulk import
            success_count, error_count, errors = PhishingSimulationService.bulk_import_employees(
                employee_data, current_user.id
            )

            flash(f'Import completed: {success_count} successful, {error_count} errors', 'info')

            if errors:
                for error in errors[:5]:  # Show first 5 errors
                    flash(error, 'warning')

            return redirect(url_for('simulation.employees'))

        except Exception as e:
            flash(f'Error processing CSV file: {str(e)}', 'error')

    return render_template('simulation/bulk_upload_employees.html', form=form)


@simulation.route('/templates')
@login_required
def email_templates():
    """List email templates"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    difficulty = request.args.get('difficulty', '')

    query = EmailTemplate.query.filter_by(created_by_id=current_user.id, is_active=True)

    if search:
        query = query.filter(
            db.or_(
                EmailTemplate.name.contains(search),
                EmailTemplate.description.contains(search),
                EmailTemplate.subject.contains(search)
            )
        )

    if category:
        query = query.filter(EmailTemplate.category == category)

    if difficulty:
        query = query.filter(EmailTemplate.difficulty_level == difficulty)

    templates = query.order_by(EmailTemplate.created_at.desc()).paginate(
        page=page, per_page=12, error_out=False
    )

    return render_template('simulation/email_templates.html', templates=templates)


@simulation.route('/templates/create', methods=['GET', 'POST'])
@login_required
def create_email_template():
    """Create a new email template"""
    form = EmailTemplateForm()

    if form.validate_on_submit():
        try:
            template = EmailTemplate(
                name=form.name.data,
                description=form.description.data,
                category=form.category.data,
                difficulty_level=form.difficulty_level.data,
                subject=form.subject.data,
                sender_name=form.sender_name.data,
                sender_email=form.sender_email.data,
                html_content=form.html_content.data,
                text_content=form.text_content.data,
                landing_page_url=form.landing_page_url.data,
                landing_page_content=form.landing_page_content.data,
                created_by_id=current_user.id
            )

            db.session.add(template)
            db.session.commit()

            flash('Email template created successfully!', 'success')
            return redirect(url_for('simulation.email_templates'))

        except Exception as e:
            flash(f'Error creating template: {str(e)}', 'error')

    return render_template('simulation/create_email_template.html', form=form)


@simulation.route('/templates/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_email_template(id):
    """Edit an email template"""
    template = EmailTemplate.query.get_or_404(id)

    if template.created_by_id != current_user.id:
        abort(403)

    form = EmailTemplateForm(obj=template)

    if form.validate_on_submit():
        try:
            template.name = form.name.data
            template.description = form.description.data
            template.category = form.category.data
            template.difficulty_level = form.difficulty_level.data
            template.subject = form.subject.data
            template.sender_name = form.sender_name.data
            template.sender_email = form.sender_email.data
            template.html_content = form.html_content.data
            template.text_content = form.text_content.data
            template.landing_page_url = form.landing_page_url.data
            template.landing_page_content = form.landing_page_content.data
            template.updated_at = datetime.utcnow()

            db.session.commit()
            flash('Email template updated successfully!', 'success')
            return redirect(url_for('simulation.email_templates'))

        except Exception as e:
            flash(f'Error updating template: {str(e)}', 'error')

    return render_template('simulation/create_email_template.html', form=form, template=template)


@simulation.route('/templates/<int:id>/preview')
@login_required
def preview_email_template(id):
    """Preview email template as JSON"""
    template = EmailTemplate.query.get_or_404(id)

    if template.created_by_id != current_user.id:
        abort(403)

    return jsonify({
        'subject': template.subject,
        'sender_name': template.sender_name,
        'sender_email': template.sender_email,
        'html_content': template.html_content,
        'text_content': template.text_content
    })


@simulation.route('/templates/<int:id>/duplicate', methods=['POST'])
@login_required
def duplicate_email_template(id):
    """Duplicate an email template"""
    template = EmailTemplate.query.get_or_404(id)

    if template.created_by_id != current_user.id:
        abort(403)

    try:
        new_template = EmailTemplate(
            name=f"{template.name} (Copy)",
            description=template.description,
            category=template.category,
            difficulty_level=template.difficulty_level,
            subject=template.subject,
            sender_name=template.sender_name,
            sender_email=template.sender_email,
            html_content=template.html_content,
            text_content=template.text_content,
            landing_page_url=template.landing_page_url,
            landing_page_content=template.landing_page_content,
            created_by_id=current_user.id
        )

        db.session.add(new_template)
        db.session.commit()

        return jsonify({'success': True, 'template_id': new_template.id})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@simulation.route('/templates/<int:id>', methods=['DELETE'])
@login_required
def delete_email_template(id):
    """Delete an email template"""
    template = EmailTemplate.query.get_or_404(id)

    if template.created_by_id != current_user.id:
        abort(403)

    try:
        # Check if template is used in any campaigns
        campaign_count = Campaign.query.filter_by(email_template_id=id).count()
        if campaign_count > 0:
            return jsonify({
                'success': False,
                'error': f'Template is used in {campaign_count} campaigns and cannot be deleted'
            })

        db.session.delete(template)
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@simulation.route('/employees/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(id):
    """Edit an employee"""
    employee = Employee.query.get_or_404(id)

    if employee.created_by_id != current_user.id:
        abort(403)

    form = EmployeeForm(obj=employee)

    if form.validate_on_submit():
        try:
            employee.email = form.email.data
            employee.first_name = form.first_name.data
            employee.last_name = form.last_name.data
            employee.department = form.department.data
            employee.position = form.position.data
            employee.employee_id = form.employee_id.data
            employee.updated_at = datetime.utcnow()

            db.session.commit()
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('simulation.employees'))

        except Exception as e:
            flash(f'Error updating employee: {str(e)}', 'error')

    return render_template('simulation/create_employee.html', form=form, employee=employee)


@simulation.route('/employees/<int:id>', methods=['DELETE'])
@login_required
def delete_employee(id):
    """Delete an employee"""
    employee = Employee.query.get_or_404(id)

    if employee.created_by_id != current_user.id:
        abort(403)

    try:
        # Soft delete - just mark as inactive
        employee.is_active = False
        employee.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@simulation.route('/training')
@login_required
def training_modules():
    """List training modules"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    difficulty = request.args.get('difficulty', '')

    query = TrainingModule.query.filter_by(is_active=True)

    if search:
        query = query.filter(
            db.or_(
                TrainingModule.title.contains(search),
                TrainingModule.description.contains(search)
            )
        )

    if category:
        query = query.filter(TrainingModule.category == category)

    if difficulty:
        query = query.filter(TrainingModule.difficulty_level == difficulty)

    training_modules = query.order_by(TrainingModule.created_at.desc()).paginate(
        page=page, per_page=12, error_out=False
    )

    return render_template('simulation/training_modules.html', training_modules=training_modules)


@simulation.route('/training/<int:id>')
@login_required
def training_module_detail(id):
    """Training module detail view"""
    module = TrainingModule.query.get_or_404(id)

    # Get or create progress record
    progress = TrainingProgress.query.filter_by(
        employee_id=current_user.id,  # Assuming user can be treated as employee
        training_module_id=id
    ).first()

    if not progress:
        progress = TrainingProgress(
            employee_id=current_user.id,
            training_module_id=id,
            status='not_started'
        )
        db.session.add(progress)
        db.session.commit()

    # Get department statistics for analytics
    department_stats = {
        'labels': ['Engineering', 'Marketing', 'Sales', 'HR'],
        'data': [85, 92, 78, 95]  # Sample completion rates
    }

    # Get all progress records for this module
    all_progress = TrainingProgress.query.filter_by(training_module_id=id).all()

    # Calculate statistics
    total_assigned = len(all_progress)
    completed = len([p for p in all_progress if p.status == 'completed'])
    in_progress = len([p for p in all_progress if p.status == 'in_progress'])
    not_started = len([p for p in all_progress if p.status == 'not_started'])

    completion_rate = (completed / total_assigned * 100) if total_assigned > 0 else 0

    return render_template('simulation/training_module_detail.html',
                         module=module,
                         progress=progress,
                         department_stats=department_stats,
                         progress_stats={
                             'total_assigned': total_assigned,
                             'completed': completed,
                             'in_progress': in_progress,
                             'not_started': not_started,
                             'completion_rate': completion_rate
                         })


@simulation.route('/training/create', methods=['GET', 'POST'])
@login_required
def create_training_module():
    """Create a new training module"""
    from app.views.simulation.forms import TrainingModuleForm
    from app.models.simulation import TrainingModule

    form = TrainingModuleForm()

    if form.validate_on_submit():
        try:
            # Process quiz questions from the form
            quiz_questions = []
            question_count = 1

            while f'quiz_question_{question_count}' in request.form:
                question_text = request.form.get(f'quiz_question_{question_count}')
                if question_text:
                    options = []
                    for i in range(4):  # 4 options per question
                        option_text = request.form.get(f'quiz_option_{question_count}_{i}')
                        if option_text:
                            options.append(option_text)

                    correct_answer = request.form.get(f'correct_answer_{question_count}')
                    if correct_answer is not None:
                        quiz_questions.append({
                            'id': question_count,
                            'question': question_text,
                            'options': options,
                            'correct_answer': int(correct_answer)
                        })

                question_count += 1

            # Create the training module
            module = TrainingModule(
                title=form.title.data,
                description=form.description.data,
                content=form.content.data,
                category=form.category.data,
                difficulty_level=form.difficulty_level.data,
                estimated_duration=form.estimated_duration.data,
                video_url=form.video_url.data if form.video_url.data else None,
                quiz_questions=quiz_questions if quiz_questions else None,
                created_by_id=current_user.id,
                is_active=True
            )

            db.session.add(module)
            db.session.commit()

            flash(_('Training module created successfully!'), 'success')
            return redirect(url_for('simulation.training_module_detail', id=module.id))

        except Exception as e:
            db.session.rollback()
            flash(_('An error occurred while creating the training module.'), 'error')
            logger.error(f"Error creating training module: {str(e)}")

    return render_template('simulation/create_training_module.html', form=form)


@simulation.route('/training/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_training_module(id):
    """Edit a training module"""
    from app.views.simulation.forms import TrainingModuleForm

    module = TrainingModule.query.get_or_404(id)

    # Check permission
    if module.created_by_id != current_user.id:
        abort(403)

    form = TrainingModuleForm(obj=module)

    if form.validate_on_submit():
        try:
            # Process quiz questions from the form
            quiz_questions = []
            question_count = 1

            while f'quiz_question_{question_count}' in request.form:
                question_text = request.form.get(f'quiz_question_{question_count}')
                if question_text:
                    options = []
                    for i in range(4):  # 4 options per question
                        option_text = request.form.get(f'quiz_option_{question_count}_{i}')
                        if option_text:
                            options.append(option_text)

                    correct_answer = request.form.get(f'correct_answer_{question_count}')
                    if correct_answer is not None:
                        quiz_questions.append({
                            'id': question_count,
                            'question': question_text,
                            'options': options,
                            'correct_answer': int(correct_answer)
                        })

                question_count += 1

            # Update the training module
            module.title = form.title.data
            module.description = form.description.data
            module.content = form.content.data
            module.category = form.category.data
            module.difficulty_level = form.difficulty_level.data
            module.estimated_duration = form.estimated_duration.data
            module.video_url = form.video_url.data if form.video_url.data else None
            module.quiz_questions = quiz_questions if quiz_questions else None
            module.updated_at = datetime.utcnow()

            db.session.commit()

            flash(_('Training module updated successfully!'), 'success')
            return redirect(url_for('simulation.training_module_detail', id=module.id))

        except Exception as e:
            db.session.rollback()
            flash(_('An error occurred while updating the training module.'), 'error')
            logger.error(f"Error updating training module: {str(e)}")

    return render_template('simulation/edit_training_module.html', form=form, module=module)


@simulation.route('/training/<int:id>/assign', methods=['POST'])
@login_required
def assign_training_module(id):
    """Assign training module to employees"""
    module = TrainingModule.query.get_or_404(id)

    try:
        data = request.get_json()
        assignment_type = data.get('assignment_type')
        due_date = datetime.fromisoformat(data.get('due_date')) if data.get('due_date') else None

        assigned_count = 0

        if assignment_type == 'all':
            # Assign to all employees
            employees = Employee.query.filter_by(
                created_by_id=current_user.id,
                is_active=True
            ).all()
        elif assignment_type == 'department':
            departments = data.get('departments', [])
            employees = Employee.query.filter(
                Employee.created_by_id == current_user.id,
                Employee.is_active == True,
                Employee.department.in_(departments)
            ).all()
        elif assignment_type == 'specific':
            employee_ids = data.get('employees', [])
            employees = Employee.query.filter(
                Employee.id.in_(employee_ids),
                Employee.created_by_id == current_user.id,
                Employee.is_active == True
            ).all()
        else:
            employees = []

        # Create training progress records
        for employee in employees:
            existing = TrainingProgress.query.filter_by(
                employee_id=employee.id,
                training_module_id=id
            ).first()

            if not existing:
                progress = TrainingProgress(
                    employee_id=employee.id,
                    training_module_id=id,
                    started_at=datetime.utcnow(),
                    status='not_started'
                )
                db.session.add(progress)
                assigned_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'assigned_count': assigned_count
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@simulation.route('/training/<int:id>/submit-quiz', methods=['POST'])
@login_required
def submit_training_quiz(id):
    """Submit training module quiz"""
    module = TrainingModule.query.get_or_404(id)

    try:
        data = request.get_json()
        answers = data.get('answers', {})

        # Get or create progress record
        progress = TrainingProgress.query.filter_by(
            employee_id=current_user.id,
            training_module_id=id
        ).first()

        if not progress:
            progress = TrainingProgress(
                employee_id=current_user.id,
                training_module_id=id,
                status='in_progress'
            )
            db.session.add(progress)

        # Calculate score (simplified - would need actual quiz questions)
        total_questions = len(answers)
        correct_answers = 0

        # This is a placeholder - real implementation would check against correct answers
        for question_id, answer in answers.items():
            # Simulate random correct answers for demo
            if answer == 0:  # Assume first option is often correct
                correct_answers += 1

        score = correct_answers
        passed = (correct_answers / total_questions) >= 0.7 if total_questions > 0 else False

        # Update progress
        progress.quiz_score = score
        progress.quiz_attempts = (progress.quiz_attempts or 0) + 1
        progress.status = 'completed' if passed else 'in_progress'
        if passed and not progress.completed_at:
            progress.completed_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'score': score,
            'total': total_questions,
            'passed': passed
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@simulation.route('/training/<int:id>/export-progress')
@login_required
def export_training_progress(id):
    """Export training progress report"""
    module = TrainingModule.query.get_or_404(id)

    # This would generate and return a CSV/Excel file
    # For now, just return a JSON response
    progress_records = TrainingProgress.query.filter_by(
        training_module_id=id
    ).join(Employee).all()

    flash('Progress export feature is coming soon!', 'info')
    return redirect(url_for('simulation.training_module_detail', id=id))


@simulation.route('/training/<int:id>/send-reminders', methods=['POST'])
@login_required
def send_training_reminders(id):
    """Send reminder emails for training module"""
    module = TrainingModule.query.get_or_404(id)

    try:
        # Get employees who haven't completed the training
        incomplete_progress = TrainingProgress.query.filter_by(
            training_module_id=id,
            status='not_started'
        ).join(Employee).filter(
            Employee.created_by_id == current_user.id
        ).all()

        reminder_count = len(incomplete_progress)

        # Here you would send actual reminder emails
        # For now, just simulate the process

        return jsonify({
            'success': True,
            'reminder_count': reminder_count
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@simulation.route('/training/<int:id>', methods=['DELETE'])
@login_required
def delete_training_module(id):
    """Delete a training module"""
    module = TrainingModule.query.get_or_404(id)

    try:
        # Check if module has progress records
        progress_count = TrainingProgress.query.filter_by(training_module_id=id).count()
        if progress_count > 0:
            return jsonify({
                'success': False,
                'error': f'Module has {progress_count} progress records and cannot be deleted'
            })

        db.session.delete(module)
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@simulation.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback about phishing simulation"""
    try:
        data = request.get_json()

        # Here you would save the feedback to database
        # For now, just return success

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@simulation.route('/campaigns/<int:id>/export')
@login_required
def export_campaign_results(id):
    """Export campaign results"""
    campaign = Campaign.query.get_or_404(id)

    if campaign.created_by_id != current_user.id:
        abort(403)

    # This would generate and return a CSV/Excel file
    flash('Campaign export feature is coming soon!', 'info')
    return redirect(url_for('simulation.campaign_detail', id=id))


# Tracking endpoints (no authentication required)
@simulation.route('/track/open/<target_id>')
def track_open(target_id):
    """Track email open"""
    PhishingSimulationService.track_email_open(
        target_id,
        request.remote_addr,
        request.headers.get('User-Agent')
    )

    # Return 1x1 transparent pixel
    from flask import Response
    pixel_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'

    return Response(pixel_data, mimetype='image/png')


@simulation.route('/track/click/<target_id>')
def track_click(target_id):
    """Track link click and redirect to landing page"""
    success, landing_page_url = PhishingSimulationService.track_link_click(
        target_id,
        request.remote_addr,
        request.headers.get('User-Agent')
    )

    if success and landing_page_url:
        return redirect(landing_page_url)
    else:
        return redirect(url_for('simulation.phishing_awareness'))


@simulation.route('/awareness')
def phishing_awareness():
    """Phishing awareness landing page"""
    return render_template('simulation/phishing_awareness.html')


@simulation.route('/report/<target_id>')
def report_phishing(target_id):
    """Report phishing email"""
    success = PhishingSimulationService.report_phishing_email(target_id)

    if success:
        flash('Thank you for reporting this phishing email!', 'success')

    return render_template('simulation/report_success.html')


# API endpoints for AJAX requests
@simulation.route('/api/campaigns/<int:id>/stats')
@login_required
def campaign_stats_api(id):
    """Get campaign statistics as JSON"""
    campaign = Campaign.query.get_or_404(id)

    if campaign.created_by_id != current_user.id:
        abort(403)

    analytics = PhishingSimulationService.get_campaign_analytics(id)
    return jsonify(analytics)


@simulation.route('/api/dashboard/stats')
@login_required
def dashboard_stats_api():
    """Get dashboard statistics as JSON"""
    stats = PhishingSimulationService.get_organization_dashboard_stats(
        created_by_id=current_user.id
    )
    return jsonify(stats)


# AI Security Chat endpoints
@simulation.route('/security-chat')
def security_chat():
    """AI-powered security chat interface"""
    target_id = request.args.get('target_id')
    return render_template('simulation/security_chat.html', target_id=target_id)


@simulation.route('/security-chat/<session_id>')
def security_chat_session(session_id):
    """AI-powered security chat interface for specific session"""
    from app.models.simulation import AISecurityChat

    # Verify session exists
    chat_session = AISecurityChat.query.filter_by(session_id=session_id).first()
    if not chat_session:
        flash('Chat session not found or has expired.', 'error')
        return redirect(url_for('simulation.security_chat'))

    return render_template('simulation/security_chat.html', session_id=session_id)


@simulation.route('/security-chat/start', methods=['POST'])
def start_security_chat():
    """Start a new AI security chat session"""
    from app.models.simulation import AISecurityChat
    from app.utils.ai_chat_service import AIPhishingSecurityChat

    try:
        data = request.get_json()
        target_id = data.get('target_id')

        # Create new chat session
        chat_session = AISecurityChat(
            target_id=target_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

        if current_user.is_authenticated:
            chat_session.user_id = current_user.id

        db.session.add(chat_session)
        db.session.commit()

        # Get welcome message from AI
        ai_service = AIPhishingSecurityChat()
        welcome_response = ai_service.get_ai_response(
            "Hello, I clicked on a phishing link and want to learn about security."
        )

        # Save welcome message
        from app.models.simulation import AIChatMessage
        welcome_msg = AIChatMessage(
            chat_session_id=chat_session.id,
            message=welcome_response['response'],
            is_user=False,
            ai_model='ai_service'
        )
        db.session.add(welcome_msg)
        db.session.commit()

        return jsonify({
            'success': True,
            'session_id': chat_session.session_id,
            'welcome_message': welcome_response['response'],
            'suggestions': welcome_response.get('suggestions', [])
        })

    except Exception as e:
        logger.error(f"Error starting chat session: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to start chat session'})


@simulation.route('/security-chat/<session_id>/message', methods=['POST'])
def send_chat_message(session_id):
    """Send a message to the AI security chat"""
    from app.models.simulation import AISecurityChat, AIChatMessage
    from app.utils.ai_chat_service import AIPhishingSecurityChat
    import time

    try:
        # Get chat session
        chat_session = AISecurityChat.query.filter_by(session_id=session_id).first()
        if not chat_session:
            return jsonify({'success': False, 'error': 'Chat session not found'})

        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'success': False, 'error': 'Message cannot be empty'})

        # Save user message
        user_msg = AIChatMessage(
            chat_session_id=chat_session.id,
            message=user_message,
            is_user=True
        )
        db.session.add(user_msg)

        # Get conversation history for context
        recent_messages = AIChatMessage.query.filter_by(
            chat_session_id=chat_session.id
        ).order_by(AIChatMessage.timestamp.desc()).limit(10).all()

        conversation_history = [
            {
                'message': msg.message,
                'is_user': msg.is_user,
                'timestamp': msg.timestamp
            }
            for msg in reversed(recent_messages)
        ]

        # Get AI response
        ai_service = AIPhishingSecurityChat()
        start_time = time.time()

        ai_response = ai_service.get_ai_response(user_message, conversation_history)

        response_time_ms = int((time.time() - start_time) * 1000)

        # Save AI response
        ai_msg = AIChatMessage(
            chat_session_id=chat_session.id,
            message=ai_response['response'],
            is_user=False,
            ai_model='ai_service',
            response_time_ms=response_time_ms
        )
        db.session.add(ai_msg)

        # Update session last activity
        chat_session.last_activity = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'response': ai_response['response'],
            'suggestions': ai_response.get('suggestions', []),
            'response_time_ms': response_time_ms
        })

    except Exception as e:
        logger.error(f"Error sending chat message: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to send message'})


@simulation.route('/security-chat/<session_id>/history')
def get_chat_history(session_id):
    """Get chat conversation history"""
    from app.models.simulation import AISecurityChat, AIChatMessage

    try:
        # Get chat session
        chat_session = AISecurityChat.query.filter_by(session_id=session_id).first()
        if not chat_session:
            return jsonify({'success': False, 'error': 'Chat session not found'})

        # Get messages
        messages = AIChatMessage.query.filter_by(
            chat_session_id=chat_session.id
        ).order_by(AIChatMessage.timestamp.asc()).all()

        return jsonify({
            'success': True,
            'messages': [msg.to_dict() for msg in messages],
            'session_info': chat_session.to_dict()
        })

    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to get chat history'})
