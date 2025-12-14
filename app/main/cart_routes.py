from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.main import bp
from app.models import Book, Cart, CartItem

@bp.route('/cart/add/<int:book_id>', methods=['POST'])
@login_required
def add_to_cart(book_id):
    book = Book.query.get_or_404(book_id)
    action = request.form.get('action') # 'borrow' or 'buy'
    
    # Borrowing specific checks
    if action == 'borrow':
        if book.item_type == 'sale':
            flash('This item is for Sale only.', 'danger')
            return redirect(url_for('main.inventory'))
    elif action == 'buy':
        if book.item_type == 'circulation':
            flash('This item is for Borrowing only.', 'danger')
            return redirect(url_for('main.inventory'))
            
    # Get or Create Cart
    cart = current_user.cart
    if not cart:
        cart = Cart(user=current_user)
        db.session.add(cart)
    
    # Add Item
    cart_item = CartItem.query.filter_by(cart=cart, book=book, action=action).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(cart=cart, book=book, quantity=1, action=action)
        db.session.add(cart_item)
        
    db.session.commit()
    
    # Check for AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True, 
            'cart_count': current_user.cart.items.count()
        })

    flash(f'Added {book.title} to cart for {action}!', 'success')
    return redirect(request.referrer or url_for('main.index'))

@bp.route('/cart')
@login_required
def view_cart():
    cart = current_user.cart
    if not cart:
        return render_template('cart.html', items=[], total=0)
    
    items = cart.items.all()
    # Calculate Subtotal (only for buying)
    subtotal = sum(item.book.sale_price * item.quantity for item in items if item.action == 'buy')
    return render_template('cart.html', items=items, subtotal=subtotal)

@bp.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_quantity(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.cart.user != current_user:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    action = data.get('action') # 'increase' or 'decrease'
    
    if action == 'increase':
        # Check stock for buying
        if item.action == 'buy' and item.book.stock_available <= item.quantity:
             return jsonify({'success': False, 'error': 'Not enough stock'}), 400
        item.quantity += 1
    elif action == 'decrease':
        if item.quantity > 1:
            item.quantity -= 1
        else:
             # delete if 0? For now keep at 1 or allow client to call remove
             pass
             
    db.session.commit()
    
    # Recalculate item total and possible subtotal can be done on client or returned
    return jsonify({
        'success': True, 
        'quantity': item.quantity,
        'item_total': item.book.sale_price * item.quantity if item.action == 'buy' else 0,
        'price': item.book.sale_price
    })

@bp.route('/cart/remove/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.cart.user != current_user:
        flash('Unauthorized', 'danger')
        return redirect(url_for('main.index'))
        
    db.session.delete(item)
    db.session.commit()
    flash('Item removed from cart.', 'info')
    return redirect(url_for('main.view_cart'))
