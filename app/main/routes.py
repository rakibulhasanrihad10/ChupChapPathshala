from flask import render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from app.main import bp
from app.models import Book, User, Loan, Campaign, Category, SupplyOrder, Sale
from app import db
from app.decorators import admin_required
from app.main import featured_books_routes
from app.main.inventory_forms import EditForm
from datetime import datetime

@bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_staff():
        flash('Access denied: Unauthorized.', 'danger')
        return redirect(url_for('main.index'))
    
    from datetime import datetime, timedelta
    from sqlalchemy import func, desc
    
    # Basic Stats
    total_users = User.query.count()
    total_books = Book.query.count()
    active_loans = Loan.query.filter_by(status='active').count()
    pending_orders = SupplyOrder.query.filter(SupplyOrder.status.in_(['shortlist', 'pending_review', 'placed'])).count()
    
    # Enhanced Stats with Trends
    now = datetime.utcnow()
    last_month = now - timedelta(days=30)
    last_week = now - timedelta(days=7)
    
    # Calculate trends (comparing last 7 days vs previous 7 days)
    def calculate_trend(current_count, previous_count):
        if previous_count == 0:
            return {'direction': 'up' if current_count > 0 else 'neutral', 'percentage': 0}
        change = ((current_count - previous_count) / previous_count) * 100
        return {
            'direction': 'up' if change > 0 else 'down' if change < 0 else 'neutral',
            'percentage': abs(round(change, 1))
        }
    
    # User trend (simplified - would need created_at field for accuracy)
    users_last_week = User.query.count()  
    users_prev_week = max(0, users_last_week - 2)  
    user_trend = calculate_trend(users_last_week, users_prev_week)
    

    
    # Book trend (simplified)
    books_trend = {'direction': 'neutral', 'percentage': 0}
    
    # Overdue Loans
    overdue_loans = Loan.query.filter(
        Loan.status == 'active',
        Loan.due_date < now
    ).all()
    overdue_count = len(overdue_loans)
    
    # Stock Alerts (books with low stock)
    STOCK_THRESHOLD = 5
    low_stock_books = Book.query.filter(Book.stock_available < STOCK_THRESHOLD).all()
    stock_alerts_count = len(low_stock_books)
    
    # Recent Activity (last 10 loans/returns)
    recent_loans = Loan.query.order_by(desc(Loan.checkout_date)).limit(5).all()
    recent_returns = Loan.query.filter(Loan.return_date.isnot(None)).order_by(desc(Loan.return_date)).limit(5).all()
    
    # Combine and sort recent activity
    recent_activity = []
    for loan in recent_loans:
        recent_activity.append({
            'type': 'borrow',
            'user': loan.user.username if loan.user else 'Unknown',
            'book': loan.book.title if loan.book else 'Unknown',
            'date': loan.checkout_date,
            'icon': 'fa-book-reader',
            'color': 'blue'
        })
    for loan in recent_returns:
        recent_activity.append({
            'type': 'return',
            'user': loan.user.username if loan.user else 'Unknown',
            'book': loan.book.title if loan.book else 'Unknown',
            'date': loan.return_date,
            'icon': 'fa-undo',
            'color': 'green'
        })
    recent_activity.sort(key=lambda x: x['date'], reverse=True)
    recent_activity = recent_activity[:10]
    
    # Sales Trend Data (last 30 days) - Replaces Borrowing Trend
    sales_trend = []
    for i in range(30, -1, -1):
        date = now - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        count = Sale.query.filter(
            Sale.sale_date >= date_start,
            Sale.sale_date <= date_end
        ).count()
        
        sales_trend.append({
            'date': date.strftime('%m/%d'),
            'count': count
        })
    
    # Top Selling Books (Most Sold)
    top_selling_data = db.session.query(
        Book.title,
        func.count(Sale.id).label('sale_count')
    ).join(Sale, Sale.book_id == Book.id)\
     .group_by(Book.id, Book.title)\
     .order_by(desc('sale_count'))\
     .limit(5).all()
    
    top_selling_books = [{'title': title, 'count': count} for title, count in top_selling_data]
    
    # Stock Distribution by Category
    stock_by_category = db.session.query(
        Book.category,
        func.sum(Book.stock_available).label('total_stock')
    ).group_by(Book.category).all()
    
    category_data = [{'category': cat or 'Uncategorized', 'stock': int(stock or 0)} for cat, stock in stock_by_category]
    
    stats = {
        'total_users': total_users,
        'total_books': total_books,
        'active_loans': active_loans,
        'pending_supply_orders': pending_orders,
        'user_trend': user_trend,
        'books_trend': books_trend,
        'overdue_count': overdue_count,
        'stock_alerts_count': stock_alerts_count,
        'overdue_loans': overdue_loans[:5],  # Top 5 overdue
        'low_stock_books': low_stock_books[:5],  # Top 5 low stock
        'recent_activity': recent_activity,
        'sales_trend': sales_trend,
        'top_selling_books': top_selling_books,
        'category_data': category_data
    }
    
    return render_template('admin/dashboard.html', stats=stats)



from flask import render_template
from flask_login import login_required, current_user

from app.models import (
    Loan,
    Sale,
    ForumPost,
    Cart
)

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
