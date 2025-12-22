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
    from app.forms import CheckoutForm
    
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
    
    # Create form and pre-populate with user data
    form = CheckoutForm()
    form.name.data = current_user.username

    return render_template('checkout.html', 
                           form=form,
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
    from app.forms import CheckoutForm
    form = CheckoutForm()
    
    # Pre-populate name if form is empty
    if not form.name.data:
        form.name.data = current_user.username
    
    cart = current_user.cart
    if not cart:
        return redirect(url_for('main.index'))
    
    selected_ids_str = request.form.get('selected_ids')
    if not selected_ids_str:
        return redirect(url_for('main.view_cart'))
    
    selected_ids = selected_ids_str.split(',')
    coupon_code = request.form.get('coupon_code')
    
    # Validate form
    if not form.validate_on_submit():
        # Re-render checkout page with errors
        all_items = cart.items.all()
        items = [item for item in all_items if str(item.id) in selected_ids]
        subtotal = sum(item.book.sale_price * item.quantity for item in items if item.action == 'buy')
        delivery_charge = 60.0 if subtotal > 0 else 0
        
        # Calculate discount
        discount_amount = 0
        if coupon_code:
            discount_obj = Discount.query.filter_by(code=coupon_code).first()
            if discount_obj and discount_obj.is_valid():
                if discount_obj.discount_type == 'percent':
                    discount_amount = subtotal * (discount_obj.value/100)
                elif discount_obj.discount_type == 'fixed':
                    discount_amount = discount_obj.value
        
        total = subtotal + delivery_charge - discount_amount
        
        # Flash validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
        
        return render_template('checkout.html',
                             form=form,
                             items=items,
                             subtotal=subtotal,
                             delivery_charge=delivery_charge,
                             total=total,
                             discount=discount_amount,
                             coupon_code=coupon_code,
                             selected_ids=selected_ids_str)
    
    # Get shipping info from form
    shipping_name = form.name.data
    shipping_phone = form.phone.data
    shipping_address = form.address.data
    
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
            'city': None  # Not collected anymore
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
