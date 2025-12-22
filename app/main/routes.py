from flask import render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from app.main import bp
from app.models import Book, User, Loan, Campaign, Category, SupplyOrder, Sale, ManagementMember
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
    
    # Recent Activity (Paginated)
    activity_page = request.args.get('activity_page', 1, type=int)
    activity_per_page = request.args.get('activity_per_page', 5, type=int)
    
    from sqlalchemy import union_all, literal_column
    
    # Unified Query for Recent Activity
    # Type 1: Borrow
    q_borrow = db.session.query(
        literal_column("'borrow'").label('type'),
        User.username.label('user'),
        Book.title.label('book'),
        Loan.checkout_date.label('date'),
        literal_column("'fa-book-reader'").label('icon'),
        literal_column("'blue'").label('color')
    ).join(User, Loan.user_id == User.id)\
     .join(Book, Loan.book_id == Book.id)\
     .filter(Loan.checkout_date.isnot(None))

    # Type 2: Return
    q_return = db.session.query(
        literal_column("'return'").label('type'),
        User.username.label('user'),
        Book.title.label('book'),
        Loan.return_date.label('date'),
        literal_column("'fa-undo'").label('icon'),
        literal_column("'green'").label('color')
    ).join(User, Loan.user_id == User.id)\
     .join(Book, Loan.book_id == Book.id)\
     .filter(Loan.return_date.isnot(None))

    # Type 3: Sale
    q_sale = db.session.query(
        literal_column("'sale'").label('type'),
        User.username.label('user'),
        Book.title.label('book'),
        Sale.sale_date.label('date'),
        literal_column("'fa-shopping-cart'").label('icon'),
        literal_column("'amber'").label('color')
    ).join(User, Sale.user_id == User.id)\
     .join(Book, Sale.book_id == Book.id)

    # Combine all
    unified_activity = q_borrow.union_all(q_return, q_sale).order_by(desc('date'))
    recent_activity_pagination = unified_activity.paginate(page=activity_page, per_page=activity_per_page, error_out=False)
    recent_activity = recent_activity_pagination.items
    
    # Sales Trend Data
    # Daily (Last 30 days)
    daily_sales = []
    for i in range(29, -1, -1):
        date = now - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        count = Sale.query.filter(Sale.sale_date >= date_start, Sale.sale_date <= date_end).count()
        daily_sales.append({'label': date.strftime('%m/%d'), 'count': count})

    # Monthly (Last 12 months)
    monthly_sales = []
    for i in range(11, -1, -1):
        # Calculate start of month i months ago
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Use a simple way to go back months
        month_date = first_of_this_month - timedelta(days=i*30) 
        # Adjust to the actual first day of that month
        month_start = month_date.replace(day=1)
        # Next month start
        if month_start.month == 12:
            next_month_start = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month_start = month_start.replace(month=month_start.month + 1)
        
        count = Sale.query.filter(Sale.sale_date >= month_start, Sale.sale_date < next_month_start).count()
        monthly_sales.append({'label': month_start.strftime('%b %Y'), 'count': count})

    # Yearly (Last 5 years)
    yearly_sales = []
    for i in range(4, -1, -1):
        year_start = now.replace(year=now.year - i, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        year_end = year_start.replace(year=year_start.year + 1)
        count = Sale.query.filter(Sale.sale_date >= year_start, Sale.sale_date < year_end).count()
        yearly_sales.append({'label': year_start.strftime('%Y'), 'count': count})

    sales_trends = {
        'daily': daily_sales,
        'monthly': monthly_sales,
        'yearly': yearly_sales
    }
    
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
    
    management_members = ManagementMember.query.order_by(ManagementMember.display_order).all()
    
    # Additional data for modals
    all_users = User.query.order_by(User.username).all()
    all_active_loans = Loan.query.filter_by(status='active').order_by(Loan.due_date).all()
    all_pending_orders = SupplyOrder.query.filter(SupplyOrder.status.in_(['shortlist', 'pending_review', 'placed'])).order_by(SupplyOrder.created_at.desc()).all()
    
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
        'low_stock_books': low_stock_books[:10],  # Top 10 low stock
        'recent_activity': recent_activity,
        'recent_activity_pagination': recent_activity_pagination,
        'sales_trends': sales_trends,
        'top_selling_books': top_selling_books,
        'category_data': category_data,
        # Modal data
        'all_users': all_users,
        'all_active_loans': all_active_loans,
        'all_pending_orders': all_pending_orders,
        'current_datetime': now  # For template datetime comparisons
    }
    
    # Only return the partial if this is a pagination request for recent activity
    if request.headers.get('HX-Request') and ('activity_page' in request.args or 'activity_per_page' in request.args):
        return render_template('admin/partials/_recent_activity.html', stats=stats)
        
    return render_template('admin/dashboard.html', stats=stats, management_members=management_members)



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
    return render_template('admin/members.html', users=users)

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
    
    return render_template('admin/offers.html', books=books, search_query=search_query)

@bp.route('/admin/loans')
@login_required
@admin_required
def admin_loans():
    loans = Loan.query.order_by(Loan.checkout_date.desc()).all()
    for loan in loans:
        if loan.status == 'active':
            delta = loan.due_date - datetime.utcnow() 
            loan.days_remaining = delta.days
    return render_template('admin/loans.html', loans=loans)

@bp.route('/admin/loans/return/<int:loan_id>', methods=['POST'])
@login_required
@admin_required
def mark_returned(loan_id):
    """Admin endpoint to mark a loan as returned."""
    try:
        from app.services import LoanService
        loan = LoanService.admin_return_loan(loan_id)
        flash(f'Book "{loan.book.title}" returned successfully.', 'success')
    except ValueError as e:
        flash(str(e), 'warning')
    except Exception as e:
        flash('An error occurred while processing the return.', 'error')
    
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
    return render_template('admin/campaigns.html', campaigns=campaigns)

@bp.route('/admin/campaigns/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_campaign():
    from app.forms import CampaignForm
    form = CampaignForm()
    
    if form.validate_on_submit():
        image_url = form.image_url.data
        
        # Handle file upload (overrides URL if provided)
        if form.image_file.data:
            filename = secure_filename(form.image_file.data.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'images', 'campaigns')
            os.makedirs(upload_folder, exist_ok=True)
            form.image_file.data.save(os.path.join(upload_folder, filename))
            image_url = url_for('static', filename=f'images/campaigns/{filename}')
        
        campaign = Campaign(
            title=form.title.data,
            description=form.description.data,
            image_url=image_url,
            button_text=form.button_text.data,
            button_link=form.button_link.data,
            is_active=form.is_active.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data
        )
        db.session.add(campaign)
        db.session.commit()
        flash('Campaign added successfully.', 'success')
        return redirect(url_for('main.admin_campaigns'))
    
    return render_template('admin/add_edit_campaign.html', form=form, campaign=None)

@bp.route('/admin/campaigns/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_campaign(id):
    from app.forms import CampaignForm
    campaign = Campaign.query.get_or_404(id)
    form = CampaignForm(obj=campaign)
    
    if form.validate_on_submit():
        campaign.title = form.title.data
        campaign.description = form.description.data
        campaign.button_text = form.button_text.data
        campaign.button_link = form.button_link.data
        campaign.is_active = form.is_active.data
        campaign.start_time = form.start_time.data
        campaign.end_time = form.end_time.data
        
        # Update image URL if provided
        if form.image_url.data:
            campaign.image_url = form.image_url.data
        
        # Handle file upload (overrides URL)
        if form.image_file.data:
            filename = secure_filename(form.image_file.data.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'images', 'campaigns')
            os.makedirs(upload_folder, exist_ok=True)
            form.image_file.data.save(os.path.join(upload_folder, filename))
            campaign.image_url = url_for('static', filename=f'images/campaigns/{filename}')
        
        db.session.commit()
        flash('Campaign updated successfully.', 'success')
        return redirect(url_for('main.admin_campaigns'))
    
    return render_template('admin/add_edit_campaign.html', form=form, campaign=campaign)

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
        
    categories = Category.query.order_by(Category.name).all()
    try:
        management_members = ManagementMember.query.order_by(ManagementMember.display_order).all()
    except:
        management_members = []
        
    return render_template('index.html', books=books, campaigns=campaigns, categories=categories, management_members=management_members)

@bp.route('/catalog')
def catalog():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
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
            
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    books = pagination.items
        
    return render_template('catalog.html', books=books, current_category=category, 
                           current_author=author, categories=categories, 
                           authors=authors, current_sort=sort, 
                           pagination=pagination, current_per_page=per_page)

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
    
    loan_page = request.args.get('loan_page', 1, type=int)
    sale_page = request.args.get('sale_page', 1, type=int)
    forum_page = request.args.get('forum_page', 1, type=int)
    loan_per_page = request.args.get('loan_per_page', 5, type=int)
    sale_per_page = request.args.get('sale_per_page', 5, type=int)
    forum_per_page = request.args.get('forum_per_page', 5, type=int)
    loan_filter = request.args.get('loan_filter', 'all')
    
    # Paginate forum posts (Forum Activity) - Publicly visible
    forum_pagination = ForumPost.query.filter_by(user_id=user.id).order_by(ForumPost.created_at.desc()).paginate(page=forum_page, per_page=forum_per_page, error_out=False)
    forum_posts = forum_pagination.items
    
    forum_posts = forum_pagination.items
    
    # Initialize private variables for public view
    loans = []
    sales = None
    active_loans = []
    overdue_loans = []
    loans_pagination = None
    
    if current_user.is_authenticated and current_user.id == user.id:
        # Paginate loans (Borrowing History)
        query = Loan.query.filter_by(user_id=user.id)
        
        if loan_filter == 'active':
            query = query.filter_by(status='active')
        elif loan_filter == 'returned':
            query = query.filter_by(status='returned')
            
        # Sort: Active first (asc works because 'active' < 'returned'), then checkout date desc
        loans_pagination = query.order_by(Loan.status.asc(), Loan.checkout_date.desc()).paginate(page=loan_page, per_page=loan_per_page, error_out=False)
        loans = loans_pagination.items
        
        # Paginate sales (Purchase History)
        sales = Sale.query.filter_by(user_id=user.id).order_by(Sale.sale_date.desc()).paginate(page=sale_page, per_page=sale_per_page, error_out=False)
        
        # Stats are calculated from all active loans (not just current page)
        all_active = Loan.query.filter_by(user_id=user.id, status='active').all()
        active_loans = all_active
        overdue_loans = [l for l in all_active if l.due_date < datetime.utcnow()]
        
        # Calculate days remaining for loans on the current page
        for loan in loans:
            if loan.status == 'active':
                delta = loan.due_date - datetime.utcnow()
                loan.days_remaining = delta.days
    
    return render_template('profile.html', user=user, loans=loans, sales=sales, 
                           forum_posts=forum_posts, forum_pagination=forum_pagination,
                           loans_pagination=loans_pagination,
                           loan_per_page=loan_per_page, sale_per_page=sale_per_page,
                           forum_per_page=forum_per_page, loan_filter=loan_filter,
                           active_loans=active_loans, overdue_loans=overdue_loans)

@bp.route('/admin/management/update', methods=['POST'])
@login_required
@admin_required
def update_management_member():
    member_id = request.form.get('id')
    member = ManagementMember.query.get(member_id)
    if not member:
        flash('Member not found', 'danger')
        return redirect(url_for('main.admin_dashboard'))
    
    if request.form.get('name'):
        member.name = request.form.get('name')
    if request.form.get('designation'):
        member.designation = request.form.get('designation')
        
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            import uuid
            _, ext = os.path.splitext(filename)
            unique_filename = f"management_{member.id}_{uuid.uuid4().hex[:8]}{ext}"
            
            # Save to 'app/static/images'
            images_dir = os.path.join(current_app.root_path, 'static', 'images')
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)
            
            file.save(os.path.join(images_dir, unique_filename))
            member.image_file = f"images/{unique_filename}"
            
    db.session.commit()
    flash('Member updated successfully', 'success')
    return redirect(url_for('main.admin_dashboard'))
