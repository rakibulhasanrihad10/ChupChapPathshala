from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.main import bp
from app.models import Book, Sale, Loan, Discount

@bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    cart = current_user.cart
    if not cart or cart.items.count() == 0:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('main.index'))
        
    coupon_code = request.form.get('coupon_code')
    items = cart.items.all()
    errors = []
    
    for item in items:
        book = item.book
        
        # Stock Check
        if book.stock_available < item.quantity:
            errors.append(f'Not enough stock for {book.title}')
            continue
            
        if item.action == 'buy':
            # Calculate Price with Discounts
            price = book.price
            
            # 1. Membership Discount (10% for Premium)
            if current_user.membership_type == 'premium':
                price *= 0.90
                
            # 2. Coupon Discount
            if coupon_code:
                discount = Discount.query.filter_by(code=coupon_code).first()
                if discount and discount.is_valid():
                    if discount.discount_type == 'percent':
                        price *= (1 - discount.value/100)
                    elif discount.discount_type == 'fixed':
                        price = max(0, price - discount.value)
                elif discount:
                     errors.append(f'Coupon {coupon_code} is expired or invalid.')

            # Create Sale Record
            for _ in range(item.quantity):
                sale = Sale(user_id=current_user.id, book_id=book.id, price_at_sale=price)
                db.session.add(sale)
                
            # Update Stock
            book.stock_sold += item.quantity
            book.stock_available -= item.quantity
            # book.stock_total remains same for sales until audit, or we can decrement it? 
            # Usually 'sold' implies it's gone from library property, but kept in specific 'sold' counter.
            # Let's simplify: Available decreases. Total can remain to track history, or decrease. 
            # Specs say: "Mark item status as Sold and decrement stock count."
            # So let's decrement stock_total too if it's leaving the library? 
            # Or just decrement Available. Let's decrement Available.
            
        elif item.action == 'borrow':
            # Create Loan Record
            due_date = datetime.utcnow() + timedelta(days=14) # 2 weeks loan
            for _ in range(item.quantity):
                loan = Loan(user_id=current_user.id, book_id=book.id, due_date=due_date)
                db.session.add(loan)
            
            # Update Stock
            book.stock_borrowed += item.quantity
            book.stock_available -= item.quantity
            
    if errors:
        for e in errors:
            flash(e, 'danger')
        return redirect(url_for('main.view_cart'))
        
    # Clear Cart
    for item in items:
        db.session.delete(item)
    # db.session.delete(cart) # Keep cart object, just empty items? Or delete?
    # Usually empty items.
    
    db.session.commit()
    flash('Checkout successful! Receipts sent to email.', 'success')
    return redirect(url_for('main.index'))
