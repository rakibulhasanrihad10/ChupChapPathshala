from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.auth import bp
from app.auth.forms import RegistrationForm, LoginForm, CreateAdminForm
from app.models import User
from config import Config

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html', title='Register', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Login Unsuccessful. Please check email and password')
            
    return render_template('auth/login.html', title='Login', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/create_admin', methods=['GET', 'POST'])
@login_required
def create_admin():
    if not current_user.is_admin():
        flash('You do not have permission to access this page.')
        return redirect(url_for('main.index'))
    
    form = CreateAdminForm()
    admins = User.query.filter_by(role='admin').all()
    
    if form.validate_on_submit():
        # Double check domain logic here just in case, though form handles it
        domain = form.email.data.split('@')[-1]
        if f'@{domain}' not in Config.APPROVED_ADMIN_DOMAINS:
             flash("ERROR: The email address provided is not associated with an approved administrative domain. Admin creation aborted.")
             return render_template('auth/create_admin.html', title='Create New Admin', form=form, admins=admins)

        user = User(username=form.username.data, email=form.email.data, role='admin')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        # Mock Email Notification
        flash(f"Success! New Admin user ({form.name.data}) has been created and notified.")
        return redirect(url_for('auth.create_admin'))
        
    return render_template('auth/create_admin.html', title='Create New Admin', form=form, admins=admins)
