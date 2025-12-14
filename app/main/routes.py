from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.main import bp
from app.models import Book, User, Loan
from app import db
from app.decorators import admin_required
from app.main import featured_books_routes
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
        # Determine discount percentage
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
        query = query.filter(Book.title.ilike(f'%{search_query}%'))
        
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
            # Add custom attribute to the object instance for the template
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
    
    # Update Stock
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
    
    # Prevent deleting self
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

@bp.route('/')
def index():
    books = featured_books_routes.fetch_most_sold(6)
    return render_template('index.html', books=books)

@bp.route('/catalog')
def catalog():
    category = request.args.get('category')
    author = request.args.get('author')
    sort = request.args.get('sort')
    
    categories = ['Bengali', 'Islamic', 'Children', 'Academic']
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
    loans = Loan.query.filter_by(user_id=current_user.id).order_by(Loan.checkout_date.desc()).all()
    # Calculate days remaining/overdue for each loan
    for loan in loans:
        if loan.status == 'active':
            delta = loan.due_date - datetime.utcnow()
            loan.days_remaining = delta.days
            
    return render_template('profile.html', loans=loans)
