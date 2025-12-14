from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.main import bp
from app.models import Book, Sale, Loan, Discount
from flask_mail import Message
from app.extensions import mail
from flask import current_app

@bp.route('/checkout/review', methods=['POST'])
@login_required
def checkout_review():
    cart = current_user.cart
    if not cart:
        flash('Cart is empty', 'warning')
        return redirect(url_for('main.index'))

    # Get Selected Items
    selected_ids = request.form.getlist('selected_items')
    coupon_code = request.form.get('coupon_code')
    
    if not selected_ids:
        flash('Please select at least one item to checkout.', 'warning')
        return redirect(url_for('main.view_cart'))

    # Filter Items
    all_items = cart.items.all()
    selected_items = [item for item in all_items if str(item.id) in selected_ids]
    
    if not selected_items:
        flash('No valid items selected.', 'warning')
        return redirect(url_for('main.view_cart'))

    # Calculate Totals
    subtotal = sum(item.book.sale_price * item.quantity for item in selected_items if item.action == 'buy')
    delivery_charge = 60.0 if subtotal > 0 else 0
    total = subtotal + delivery_charge
    
    discount_amount = 0
    # Coupon 
    if coupon_code:
        discount = Discount.query.filter_by(code=coupon_code).first()
        if discount and discount.is_valid():
             if discount.discount_type == 'percent':
                 discount_amount = subtotal * (discount.value/100)
             elif discount.discount_type == 'fixed':
                 discount_amount = discount.value
             total -= discount_amount

    return render_template('checkout.html', 
                           items=selected_items, 
                           subtotal=subtotal, 
                           delivery_charge=delivery_charge, 
                           total=total,
                           discount=discount_amount,
                           coupon_code=coupon_code,
                           selected_ids=','.join(selected_ids))

@bp.route('/checkout/confirm', methods=['POST'])
@login_required
def confirm_checkout():
    cart = current_user.cart
    if not cart:
        return redirect(url_for('main.index'))
        
    selected_ids_str = request.form.get('selected_ids')
    if not selected_ids_str:
        return redirect(url_for('main.view_cart'))
        
    selected_ids = selected_ids_str.split(',')
    coupon_code = request.form.get('coupon_code')
    
    # Shipping Info
    shipping_name = request.form.get('name')
    shipping_phone = request.form.get('phone')
    shipping_address = request.form.get('address')
    shipping_city = request.form.get('city')

    
    all_items = cart.items.all()
    items = [item for item in all_items if str(item.id) in selected_ids]
    errors = []
    
    for item in items:
        book = item.book
        
        # Stock Check
        if book.stock_available < item.quantity:
            errors.append(f'Not enough stock for {book.title}')
            continue
            
        if item.action == 'buy':
            # Calculate Price with Discounts
            price = book.sale_price
            
            # Membership Discount (10% for Premium)
            if current_user.membership_type == 'premium':
                price *= 0.90
                
            # Coupon Discount
            if coupon_code:
                discount = Discount.query.filter_by(code=coupon_code).first()
                if discount and discount.is_valid():
                    if discount.discount_type == 'percent':
                        price *= (1 - discount.value/100)
                    elif discount.discount_type == 'fixed':
                        price = max(0, price - discount.value)
                elif discount:
                     pass 

            # Create Sale Record
            for _ in range(item.quantity):
                sale = Sale(user_id=current_user.id, book_id=book.id, price_at_sale=price)
                db.session.add(sale)
                
            # Update Stock
            book.stock_sold += item.quantity
            book.stock_available -= item.quantity
            
        elif item.action == 'borrow':
            # Create Loan Record
            due_date = datetime.utcnow() + timedelta(days=14) 
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
        
    # Clear Processed Items from Cart
    for item in items:
        db.session.delete(item)
    
    db.session.commit()
    
    # Send Confirmation Email
    try:
        delivery_info = {
            'name': shipping_name,
            'phone': shipping_phone,
            'address': shipping_address,
            'city': shipping_city
        }

        send_order_email(current_user, items, delivery_info)
    except Exception as e:
        print(f"Failed to send email: {e}")
        
    flash('Order placed successfully! Thank you. A confirmation email has been sent.', 'success')
    return redirect(url_for('main.index'))

def send_order_email(user, items, delivery_info):
    msg = Message('Order Confirmation - ChupChap Pathshala',
                  sender=("ChupChap Support", current_app.config['ADMINS'][0]),
                  recipients=[user.email])
    
    # Text Body
    item_list = ""
    total = 0
    for item in items:

        line_total = item.book.sale_price * item.quantity
        item_list += f"- {item.book.title} x {item.quantity}: TK {line_total}\n"
        total += line_total
    
    delivery_charge = 60.0 if total > 0 else 0
    grand_total = total + delivery_charge


    msg.body = f'''Hello {user.username},

Thank you for your order! We have received your request.

Order Details:
{item_list}
Subtotal: TK {total}
Delivery Charge: TK {delivery_charge}
Total: TK {grand_total}

Shipping To:
{delivery_info['name']}
{delivery_info['phone']}
{delivery_info['address']}
{delivery_info['city']}

We will contact you shortly for delivery.

Best regards,
ChupChap Pathshala Team
'''
    mail.send(msg)
