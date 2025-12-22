from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.main import bp
from app.models import Book, Cart, CartItem
from app.services import CartService

@bp.route('/cart/add/<int:book_id>', methods=['POST'])
@login_required
def add_to_cart(book_id):
    """Add an item to the cart."""
    action = request.form.get('action')  # 'borrow' or 'buy'
    
    try:
        cart_item, created = CartService.add_item(current_user, book_id, action)
        
        # Check for AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'cart_count': CartService.get_cart_count(current_user)
            })
        
        flash(f'Added {cart_item.book.title} to cart for {action}!', 'success')
    except ValueError as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)}), 400
        flash(str(e), 'danger')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'An error occurred'}), 500
        flash('An error occurred while adding to cart.', 'danger')
    
    return redirect(request.referrer or url_for('main.index'))

@bp.route('/cart')
@login_required
def view_cart():
    """View the shopping cart."""
    items = CartService.get_cart_items(current_user)
    subtotal = CartService.calculate_subtotal(current_user)
    return render_template('cart.html', items=items, subtotal=subtotal)

@bp.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_quantity(item_id):
    """Update the quantity of a cart item."""
    data = request.get_json()
    action = data.get('action')  # 'increase' or 'decrease'
    
    try:
        item = CartService.update_quantity(item_id, current_user, action)
        
        return jsonify({
            'success': True,
            'quantity': item.quantity,
            'item_total': item.book.sale_price * item.quantity if item.action == 'buy' else 0,
            'price': item.book.sale_price
        })
    except PermissionError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'An error occurred'}), 500

@bp.route('/cart/remove/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    """Remove an item from the cart."""
    try:
        CartService.remove_item(item_id, current_user)
        flash('Item removed from cart.', 'info')
    except PermissionError:
        flash('Unauthorized', 'danger')
    except Exception:
        flash('An error occurred while removing the item.', 'danger')
    
    return redirect(url_for('main.view_cart'))
