from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.main import bp
from app.models import Book
from app.decorators import staff_required

from app.main.restock_form import RestockForm

@bp.route('/inventory')
@login_required
@staff_required
def inventory():
    books = Book.query.all()
    return render_template('inventory.html', books=books)

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
