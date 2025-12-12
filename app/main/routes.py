from flask import render_template, request
from flask_login import login_required
from app.main import bp
from app.models import Book, User
from app.decorators import admin_required
from app.main import featured_books_routes

@bp.route('/members')
@login_required
@admin_required
def members():
    users = User.query.all()
    return render_template('members.html', users=users)

@bp.route('/')
def index():
    books = featured_books_routes.fetch_most_sold(6)
    return render_template('index.html', books=books)

@bp.route('/catalog')
def catalog():
    category = request.args.get('category')
    categories = ['Bengali', 'Islamic', 'Children', 'Academic']
    
    if category:
        books = Book.query.filter_by(category=category).all()
    else:
        books = Book.query.all()
        
    return render_template('catalog.html', books=books, current_category=category, categories=categories)

@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')
