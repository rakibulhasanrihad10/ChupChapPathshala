from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.main import bp
from app.models import Book
from app.decorators import staff_required

from app.main.inventory_forms import RestockForm, EditForm

class PaginateProxy:
    def __init__(self,items):
        self.items = items

@bp.route('/inventory')
@login_required
@staff_required
def inventory():
    target = request.args.get('target',None,type=int)
    if target:
        books = PaginateProxy([Book.query.get(target)])
        return render_template('inventory.html', books=books, single=True)
    page = request.args.get('page', 1, type=int)
    books = Book.query.paginate(page=page, per_page=10, error_out=False)
    return render_template('inventory.html', books=books, single=False)

@bp.route('/inventory/add', methods=['GET', 'POST'])
@login_required
@staff_required
def add_book():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        price = float(request.form.get('price'))
        item_type = request.form.get('item_type')
        location = request.form.get('location')
        stock_total = int(request.form.get('stock_total'))
        image_url = request.form.get('image_url')
        category = request.form.get('category')
        
        book = Book(
            title=title,
            author=author,
            price=price,
            item_type=item_type,
            category=category,
            location=location,
            stock_total=stock_total,
            stock_available=stock_total, # Initially all available
            image_url=image_url if image_url else None
        )
        db.session.add(book)
        db.session.commit()
        flash('Book added to inventory!')
        return redirect(url_for('main.inventory'))
    return render_template('add_book.html')



@bp.route("/inventory/restock/<int:book_id>", methods=["GET", "POST"])
@login_required
@staff_required
def restock_book(book_id):
    book = Book.query.get_or_404(book_id)
    form = RestockForm()

    if form.validate_on_submit():
        qty = form.quantity.data

        # Update stock
        book.stock_total += qty
        book.stock_available += qty

        db.session.commit()
        flash(f"Successfully restocked {qty} copies of '{book.title}'.", "success")
        return redirect(url_for("main.inventory"))

    return render_template("restock.html", form=form, book=book)


@bp.route("/inventory/edit/<int:book_id>", methods=["GET", "POST"])
@login_required
@staff_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    form = EditForm()
    if request.method == "GET":
        form.title.data = book.title
        form.author.data = book.author
        form.price.data = book.price
        form.item_type.data = book.item_type
        form.category.data = book.category
        form.location.data = book.location
        form.image_url.data = book.image_url
        form.stock_available.data = book.stock_available
        form.stock_borrowed.data = book.stock_borrowed
        form.stock_sold.data = book.stock_sold

    
    if form.validate_on_submit():
        book.title = form.title.data
        book.author = form.author.data
        book.price = form.price.data
        book.item_type = form.item_type.data
        book.category = form.category.data
        book.location = form.location.data
        book.image_url = form.image_url.data
        book.stock_available = form.stock_available.data
        book.stock_borrowed = form.stock_borrowed.data
        book.stock_sold = form.stock_sold.data
        book.stock_total = book.stock_borrowed + book.stock_sold + book.stock_available
                
        db.session.commit()
        flash(f"Successfully Edited '{book.title}'.", "success")
        return redirect(url_for("main.inventory"))

    return render_template("edit_book.html", form=form, book=book)


@bp.route('/inventory/delete/<int:book_id>', methods=['POST'])
@login_required
@staff_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Validation: Cannot delete if currently borrowed
    if book.stock_borrowed > 0:
        flash('Cannot delete book: One or more copies are currently borrowed.', 'danger')
        return redirect(url_for('main.inventory'))

    try:
        db.session.delete(book)
        db.session.commit()
        flash('Book removed successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        # This handles other FK constraints like past sales history
        flash('Cannot delete book because it has associated history (sales, past loans).', 'danger')
    return redirect(url_for('main.inventory'))
