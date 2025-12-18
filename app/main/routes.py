from flask import render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from app.main import bp
from app.models import Book, User, Loan, Campaign, Category
from app import db
from app.decorators import admin_required
from app.main import featured_books_routes
from app.main.inventory_forms import EditForm
from datetime import datetime

@bp.route('/members')
@login_required
@admin_required
def members():
    users = User.query.all()
    return render_template('members.html', users=users)

@bp.route('/admin/offers', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_offers():
    if request.method == 'POST':
        action = request.form.get('action')
        preset = request.form.get('discount_preset')
        custom = request.form.get('custom_discount')
        
        discount = 0.0
        if preset:
            discount = float(preset)
        elif custom:
            try:
                discount = float(custom)
            except ValueError:
                discount = 0.0
                
        book_ids = request.form.getlist('book_ids')
        
        if not book_ids:
            flash('No books selected.', 'warning')
            return redirect(url_for('main.admin_offers'))
        try:
            book_ids = [int(bid) for bid in book_ids]
        except ValueError:
             pass 

        books = Book.query.filter(Book.id.in_(book_ids)).all()
        count = 0
        for book in books:
            if action == 'apply':
                book.discount_percentage = discount
                count += 1
            elif action == 'remove':
                book.discount_percentage = 0.0
                count += 1
        
        db.session.commit()
        if action == 'remove':
            flash(f'Offers removed from {count} books.', 'success')
        else:
            flash(f'Offer of {discount}% applied to {count} books.', 'success')
        return redirect(url_for('main.admin_offers'))

    query = Book.query
    search_query = request.args.get('q')
    if search_query:
        query = query.filter(Book.title.ilike(f'{search_query}%'))
        
    page = request.args.get('page', 1, type=int)
    books = query.order_by(Book.title).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('admin_offers.html', books=books, search_query=search_query)

@bp.route('/admin/loans')
@login_required
@admin_required
def admin_loans():
    loans = Loan.query.order_by(Loan.checkout_date.desc()).all()
    for loan in loans:
        if loan.status == 'active':
            delta = loan.due_date - datetime.utcnow() 
            loan.days_remaining = delta.days
    return render_template('admin_loans.html', loans=loans)

@bp.route('/admin/loans/return/<int:loan_id>', methods=['POST'])
@login_required
@admin_required
def mark_returned(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.status != 'active':
        flash('Loan is already returned or invalid.', 'warning')
        return redirect(url_for('main.admin_loans'))
        
    loan.status = 'returned'
    loan.return_date = datetime.utcnow()
    
    book = loan.book
    if book:
        book.stock_borrowed = max(0, book.stock_borrowed - 1)
        book.stock_available += 1
        
    db.session.commit()
    flash(f'Book returned successfully.', 'success')
    return redirect(url_for('main.admin_loans'))

@bp.route('/members/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('main.members'))

    
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'Member {user.username} has been deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the user.', 'error')
        
    return redirect(url_for('main.members'))

# --- Campaign Management Routes ---
@bp.route('/admin/campaigns')
@login_required
@admin_required
def admin_campaigns():
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    return render_template('admin_campaigns.html', campaigns=campaigns)

@bp.route('/admin/campaigns/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_campaign():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        image_url = request.form.get('image_url')
        button_text = request.form.get('button_text')
        button_link = request.form.get('button_link')
        
        # Handle File Upload
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'images', 'campaigns')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                image_url = url_for('static', filename=f'images/campaigns/{filename}')

        # Parse Dates
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        
        start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M') if start_time_str else None
        end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M') if end_time_str else None

        campaign = Campaign(
            title=title,
            description=description,
            image_url=image_url if image_url else None,
            button_text=button_text,
            button_link=button_link,
            is_active=True,
            start_time=start_time,
            end_time=end_time
        )
        db.session.add(campaign)
        db.session.commit()
        flash('Campaign added successfully.', 'success')
        return redirect(url_for('main.admin_campaigns'))
    return render_template('add_edit_campaign.html')

@bp.route('/admin/campaigns/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_campaign(id):
    campaign = Campaign.query.get_or_404(id)
    if request.method == 'POST':
        campaign.title = request.form.get('title')
        campaign.description = request.form.get('description')
        new_url = request.form.get('image_url')
        if new_url:
            campaign.image_url = new_url
        campaign.button_text = request.form.get('button_text')
        campaign.button_link = request.form.get('button_link')
        campaign.is_active = 'is_active' in request.form
        
        # Date Updates
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        campaign.start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M') if start_time_str else None
        campaign.end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M') if end_time_str else None
        
        # Handle File Upload (Override URL)
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'images', 'campaigns')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                campaign.image_url = url_for('static', filename=f'images/campaigns/{filename}')
        
        db.session.commit()
        flash('Campaign updated successfully.', 'success')
        return redirect(url_for('main.admin_campaigns'))
        
    return render_template('add_edit_campaign.html', campaign=campaign)

@bp.route('/admin/campaigns/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_campaign(id):
    campaign = Campaign.query.get_or_404(id)
    try:
        db.session.delete(campaign)
        db.session.commit()
        flash('Campaign deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting campaign.', 'error')
    return redirect(url_for('main.admin_campaigns'))

@bp.route('/')
def index():
    books = featured_books_routes.fetch_most_sold(6)
    try:
        now = datetime.utcnow()
        from sqlalchemy import or_
        campaigns = Campaign.query.filter(
            Campaign.is_active == True,
            or_(Campaign.start_time == None, Campaign.start_time <= now),
            or_(Campaign.end_time == None, Campaign.end_time >= now)
        ).all()
    except:
        campaigns = []
        
    return render_template('index.html', books=books, campaigns=campaigns)

@bp.route('/catalog')
def catalog():
    category = request.args.get('category')
    author = request.args.get('author')
    sort = request.args.get('sort')
    
    # Fetch all categories from DB
    categories = [c.name for c in Category.query.order_by(Category.name).all()]
    # Fetch distinct authors
    authors = [a[0] for a in db.session.query(Book.author).distinct().all() if a[0]]
    
    query = Book.query
    if category:
        query = query.filter_by(category=category)
    if author:
        query = query.filter_by(author=author)

    if request.args.get('filter') == 'offers':
        query = query.filter(Book.discount_percentage > 0)
        
    if sort:
        if sort == 'a to z':
            query = query.order_by(Book.title.asc())
        elif sort == 'z to a':
            query = query.order_by(Book.title.desc())
        elif sort == 'low to high':
            query = query.order_by(Book.price.asc())
        elif sort == 'high to low':
            query = query.order_by(Book.price.desc())
            
    books = query.all()
        
    return render_template('catalog.html', books=books, current_category=category, current_author=author, categories=categories, authors=authors, current_sort=sort)

@bp.route('/profile')
@login_required
def profile():
    # My Profile
    return redirect(url_for('main.user_profile', username=current_user.username))

@bp.route('/profile/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    # Logic:
    # If Owner: Show Loans and Posts
    # If Public: Show Post Only (Loans Hidden in Template)
    
    loans = None
    if current_user.is_authenticated and current_user.id == user.id:
        loans = Loan.query.filter_by(user_id=user.id).order_by(Loan.checkout_date.desc()).all()
        # Calculate days remaining/overdue for each loan
        for loan in loans:
            if loan.status == 'active':
                delta = loan.due_date - datetime.utcnow()
                loan.days_remaining = delta.days
    
    return render_template('profile.html', user=user, loans=loans)
