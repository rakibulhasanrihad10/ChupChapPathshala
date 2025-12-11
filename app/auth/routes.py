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
    return render_template('auth/create_admin.html', title='Create New Admin', form=form, admins=admins)

from app.extensions import oauth

@bp.route('/login/google')
def google_login():
    google = oauth.create_client('google')
    redirect_uri = url_for('auth.google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@bp.route('/login/google/callback')
def google_callback():
    google = oauth.create_client('google')
    token = google.authorize_access_token()
    resp = google.get('https://www.googleapis.com/oauth2/v1/userinfo')
    user_info = resp.json()
    
    # Do we have this user?
    email = user_info['email']
    user = User.query.filter_by(email=email).first()
    
    if not user:
        # Create a new user
        # We'll use the email prefix as username, ensuring uniqueness
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1
            
        user = User(
            username=username, 
            email=email,
            role='customer', # Default role
            # No password set since it's OAuth
        )
        db.session.add(user)
        db.session.commit()
    
    login_user(user)
    return redirect(url_for('main.index'))
