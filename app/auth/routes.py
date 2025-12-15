from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.auth import bp
from app.auth.forms import RegistrationForm, LoginForm, CreateAdminForm
from app.models import User
from config import Config

@bp.before_app_request
def before_request():
    session.permanent = True


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, phone_number=form.phone_number.data)
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
    # Fetch both admins and librarians
    staff = User.query.filter(User.role.in_(['admin', 'librarian'])).all()
    
    if form.validate_on_submit():
        # Double check domain logic here just in case, though form handles it
        domain = form.email.data.split('@')[-1]
        if f'@{domain}' not in Config.APPROVED_ADMIN_DOMAINS:
             flash("ERROR: The email address provided is not associated with an approved administrative domain. Admin creation aborted.")
             return render_template('auth/create_admin.html', title='Create New Staff', form=form, staff=staff)

        user = User(username=form.username.data, email=form.email.data, role=form.role.data, phone_number=form.phone_number.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        # Mock Email Notification
        flash(f"Success! New {form.role.data.capitalize()} user ({form.name.data}) has been created and notified.")
        return redirect(url_for('auth.create_admin'))
        
    return render_template('auth/create_admin.html', title='Create New Staff', form=form, staff=staff)

@bp.route('/delete_staff/<int:user_id>', methods=['POST'])
@login_required
def delete_staff(user_id):
    if not current_user.is_admin():
        flash('Permission denied.')
        return redirect(url_for('main.index'))
        
    user = User.query.get_or_404(user_id)
    
    # Prevent self-deletion
    if user.id == current_user.id:
        flash('You cannot delete your own account.')
        return redirect(url_for('auth.create_admin'))

    # Prevent deleting other admins
    if user.role == 'admin':
        flash('You cannot delete another administrator.')
        return redirect(url_for('auth.create_admin'))
        
    # target is actually staff (safety check)
    if user.role not in ['admin', 'librarian']:
         flash('Cannot delete non-staff users from this panel.')
         return redirect(url_for('auth.create_admin'))

    db.session.delete(user)
    db.session.commit()
    flash(f'Staff member {user.username} has been deleted.')
    return redirect(url_for('auth.create_admin'))

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
    

    email = user_info['email']
    user = User.query.filter_by(email=email).first()
    
    if not user:

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

import os
from werkzeug.utils import secure_filename
from app.auth.forms import EditProfileForm

def save_picture(form_picture, folder='profile_pics'):
    # Generate random hex to avoid filename collisions
    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    

    upload_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'uploads', folder)
    

    if not os.path.exists(upload_path):
        os.makedirs(upload_path)
        
    picture_path = os.path.join(upload_path, picture_fn)
    form_picture.save(picture_path)
    

    return url_for('static', filename=f'uploads/{folder}/{picture_fn}')

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.phone_number = form.phone_number.data
        
        
        if form.profile_photo.data:
            picture_file = save_picture(form.profile_photo.data, 'profile_pics')
            current_user.profile_photo = picture_file
            
        if form.cover_photo.data:
            cover_file = save_picture(form.cover_photo.data, 'profile_pics') 
            current_user.cover_photo = cover_file
            
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('main.profile'))
        
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.phone_number.data = current_user.phone_number
        
    return render_template('auth/edit_profile.html', title='Edit Profile', form=form)

from flask_mail import Message
from app.extensions import mail
from flask import current_app
from app.auth.forms import ResetPasswordRequestForm, ResetPasswordForm

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('ChupChap Pathshala Password Reset Request',
                  sender=("ChupChap Support", current_app.config['ADMINS'][0]),
                  recipients=[user.email])
    

    reset_url = url_for('auth.reset_password', token=token, _external=True)
    msg.body = f'''To reset your password, visit the following link:
{reset_url}

If you did not make this request then simply ignore this email and no changes will be made.
'''
    
    # Send the email via Flask-Mail

    
    # Try sending if server configured, otherwise just log (handled by print above safely)
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Mail send failed (expected if no SMTP): {e}")

@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html',
                           title='Reset Password', form=form)

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)
