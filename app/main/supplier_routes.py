from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.main import bp
from app import db
from app.models import Book, SupplyOrder, SupplyOrderItem, User, Supplier
from datetime import datetime
from sqlalchemy import func

@bp.route('/supplier/orders', methods=['GET'])
@login_required
def supplier_orders():
    if not current_user.is_staff():
        flash('Access denied: Staff only.', 'danger')
        return redirect(url_for('main.index'))
    
    # Filter Parameters
    supplier_id = request.args.get('supplier_id', type=int)
    date_str = request.args.get('date')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    search_query = request.args.get('search', '').strip()
    sort_by = request.args.get('sort', 'newest')
    
    query = SupplyOrder.query
    
    if search_query:
        if search_query.startswith('#'):
            search_id = search_query[1:]
        else:
            search_id = search_query
        
        if search_id.isdigit():
            query = query.filter(SupplyOrder.id == int(search_id))
    
    if supplier_id:
        query = query.filter(SupplyOrder.supplier_id == supplier_id)
        
    # Date Filtering
    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            # Filter by exact date
            query = query.filter(func.date(SupplyOrder.created_at) == filter_date)
        except ValueError:
            pass 
            
    elif start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            # Make end_date inclusive
            end_date = end_date.replace(hour=23, minute=59, second=59)
            
            query = query.filter(SupplyOrder.created_at >= start_date, SupplyOrder.created_at <= end_date)
        except ValueError:
            pass

    # Sorting
    if sort_by == 'newest':
        query = query.order_by(SupplyOrder.created_at.desc())
    elif sort_by == 'oldest':
        query = query.order_by(SupplyOrder.created_at.asc())
        
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    orders = pagination.items
    
    # Summary Statistics (Calculated on the filtered query)
    stats = {
        'total_orders': query.count(),
        'pending': query.filter(SupplyOrder.status == 'placed').count(),
        'completed': query.filter(SupplyOrder.status == 'completed').count(),
        'total_amount': 0
    }
    
    amount_query = query.order_by(None)\
                        .join(SupplyOrderItem, SupplyOrderItem.order_id == SupplyOrder.id)\
                        .join(Book, SupplyOrderItem.book_id == Book.id)\
                        .with_entities(func.sum(SupplyOrderItem.mass * Book.price))
    
    stats['total_amount'] = amount_query.scalar() or 0

    suppliers = Supplier.query.order_by(Supplier.name).all()
    
    # Handle AJAX request for real-time updates
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
         return render_template('admin/supplier/orders_table.html', orders=orders, pagination=pagination)

    return render_template('admin/supplier/orders.html', 
                           orders=orders, 
                           pagination=pagination, 
                           suppliers=suppliers,
                           current_supplier_id=supplier_id,
                           current_date=date_str,
                           current_start_date=start_date_str,
                           current_end_date=end_date_str,
                           current_sort=sort_by,
                           stats=stats)

THRESHOLD = 5

def get_or_create_shortlist():
    # Find an active shortlist (draft) order
    order = SupplyOrder.query.filter_by(status='shortlist').first()
    if not order:
        order = SupplyOrder(status='shortlist')
        db.session.add(order)
        db.session.commit()
    return order

@bp.route('/supplier/shortlist', methods=['GET', 'POST'])
@login_required
def supplier_shortlist():
    if not current_user.is_staff():
        flash('Access denied: Staff only.', 'danger')
        return redirect(url_for('main.index'))

    
    order = get_or_create_shortlist()


    # Find all low stock books
    low_stock_books = Book.query.filter(Book.stock_available < THRESHOLD).all()
    
    # Get IDs of books already in ANY active order (shortlist, pending, placed)
    active_orders = SupplyOrder.query.filter(SupplyOrder.status.in_(['shortlist', 'pending_review', 'placed'])).all()
    existing_item_book_ids = set()
    for o in active_orders:
        for item in o.items:
            existing_item_book_ids.add(item.book_id)
    
    items_added = 0
    for book in low_stock_books:
        # If book is low stock and not already in any floating/pending order
        if book.id not in existing_item_book_ids:
            new_item = SupplyOrderItem(order_id=order.id, book_id=book.id, mass=5) 
            db.session.add(new_item)
            items_added += 1
    
    if items_added > 0:
        db.session.commit()
        if items_added == 1:
            flash(f'1 item floated up to the shortlist due to low stock.', 'info')
        else:
            flash(f'{items_added} items floated up to the shortlist due to low stock.', 'info')

    items = order.items.all()
    
    total_mass = sum(item.mass for item in items)

    return render_template('admin/supplier/shortlist.html', order=order, items=items, total_mass=total_mass)

@bp.route('/supplier/lift/<int:book_id>', methods=['POST'])
@login_required
def supplier_lift(book_id):
    if not current_user.is_staff():
        return redirect(url_for('main.index'))
        
    order = get_or_create_shortlist()
    
    # Check if already in list
    existing = SupplyOrderItem.query.filter_by(order_id=order.id, book_id=book_id).first()
    if existing:
        flash('This book is already in the shortlist.', 'warning')
    else:
        new_item = SupplyOrderItem(order_id=order.id, book_id=book_id, mass=5)
        db.session.add(new_item)
        db.session.commit()
        flash('Manual Lift applied! Book added to shortlist.', 'success')
        
    return redirect(url_for('main.supplier_shortlist'))

@bp.route('/supplier/drop/<int:item_id>', methods=['POST'])
@login_required
def supplier_drop(item_id):
    item = SupplyOrderItem.query.get_or_404(item_id)
    if item.order.status not in ['shortlist', 'pending_review']:
        flash('Cannot drop items from a locked order.', 'danger')
        return redirect(url_for('main.supplier_shortlist'))
        
    db.session.delete(item)
    db.session.commit()
    flash('Item dropped successfully.', 'success')
    
    if item.order.status == 'pending_review':
        return redirect(url_for('main.supplier_review'))
    return redirect(url_for('main.supplier_shortlist'))

@bp.route('/supplier/adjust_mass/<int:item_id>', methods=['POST'])
@login_required
def supplier_adjust_mass(item_id):
    item = SupplyOrderItem.query.get_or_404(item_id)
    if item.order.status not in ['shortlist', 'pending_review']:
        flash('Cannot adjust mass of a locked order.', 'danger')
        return redirect(url_for('main.supplier_shortlist'))
        
    action = request.form.get('action') 
    
    if action == 'increase':
        item.mass += 1
    elif action == 'decrease':
        if item.mass > 1:
            item.mass -= 1
    
    db.session.commit()
    
    if item.order.status == 'pending_review':
        return redirect(url_for('main.supplier_review'))
    return redirect(url_for('main.supplier_shortlist'))

@bp.route('/supplier/submit_review', methods=['POST'])
@login_required
def supplier_submit_review():
    order = get_or_create_shortlist()
    if order.items.count() == 0:
        flash('Shortlist is empty. Nothing to review.', 'warning')
        return redirect(url_for('main.supplier_shortlist'))
        
    order.status = 'pending_review'
    db.session.commit()
    
    flash('Order sent to Owner for Authorization.', 'success')
    return redirect(url_for('main.supplier_shortlist'))

@bp.route('/supplier/review', methods=['GET'])
@login_required
def supplier_review():
    if not current_user.is_admin():
        flash('Access denied: Owner/Admin only.', 'danger')
        return redirect(url_for('main.index'))
    
    # Find orders pending review
    orders = SupplyOrder.query.filter_by(status='pending_review').all()
    suppliers = Supplier.query.all()
    return render_template('admin/supplier/review.html', orders=orders, suppliers=suppliers)

@bp.route('/supplier/launch/<int:order_id>', methods=['POST'])
@login_required
def supplier_launch(order_id):
    if not current_user.is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))

    order = SupplyOrder.query.get_or_404(order_id)
    supplier_id = request.form.get('supplier_id')
    selected_item_ids = request.form.getlist('item_ids', type=int)

    if not selected_item_ids:
        flash('Please select at least one item to order.', 'warning')
        return redirect(url_for('main.supplier_review'))

    if not supplier_id:
        flash('Please select a supplier.', 'warning')
        return redirect(url_for('main.supplier_review'))

    supplier_id = int(supplier_id)
    all_item_ids = [item.id for item in order.items]
    
    # Check if all items are selected
    is_split = False
    if set(selected_item_ids) != set(all_item_ids):
        is_split = True

    if not is_split:
        # Standard case: Use the existing order
        order.supplier_id = supplier_id
        order.status = 'placed'
        db.session.commit()
        flash('Order Authorized! & transmitted to supplier.', 'success')
        return redirect(url_for('main.supplier_confirmation', order_id=order.id))
    else:
        # Selective case: Create a new order for selected items
        new_order = SupplyOrder(status='placed', supplier_id=supplier_id)
        db.session.add(new_order)
        db.session.flush()

        # Move selected items to the new order
        for item_id in selected_item_ids:
            item = SupplyOrderItem.query.get(item_id)
            if item and item.order_id == order.id:
                item.order_id = new_order.id
        
        db.session.commit()
        flash(f'Selective Order #{new_order.id} Authorized and split from Order #{order.id}.', 'success')
        return redirect(url_for('main.supplier_confirmation', order_id=new_order.id))

@bp.route('/supplier/confirmation/<int:order_id>', methods=['GET'])
@login_required
def supplier_confirmation(order_id):
    order = SupplyOrder.query.get_or_404(order_id)
    
    # WhatsApp Message
    items = order.items.all()
    item_details = "\n".join([f"- {item.book.title} (Qty: {item.mass})" for item in items])
    whatsapp_text = f"Hello {order.supplier.name}, Here is supply order #{order.id}:\n\n{item_details}\n\nPlease check the attached invoice."
    
    return render_template('admin/supplier/confirmation.html', order=order, whatsapp_text=whatsapp_text)

@bp.route('/supplier/preview_invoice/<int:order_id>', methods=['GET'])
@login_required
def preview_invoice(order_id):
    order = SupplyOrder.query.get_or_404(order_id)
    return render_template('admin/supplier/invoice.html', order=order)

from io import BytesIO
from xhtml2pdf import pisa
from flask import make_response

@bp.route('/supplier/download_invoice/<int:order_id>', methods=['GET'])
@login_required
def download_invoice(order_id):
    order = SupplyOrder.query.get_or_404(order_id)
    
    # Render HTML template with data
    html = render_template('admin/supplier/invoice.html', order=order)
    
    # Create PDF buffer
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer)
    
    if pisa_status.err:
        return 'We had some errors <pre>' + html + '</pre>'
        
    buffer.seek(0)
    
    # Create response
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=Invoice_{order.id}.pdf'
    
    return response

@bp.route('/supplier/receive_list', methods=['GET'])
@login_required
def supplier_receive_list():
    if not current_user.is_staff():
         return redirect(url_for('main.index'))
         
    # List orders that are placed and waiting for delivery
    orders = SupplyOrder.query.filter_by(status='placed').all()
    return render_template('admin/supplier/receive_list.html', orders=orders)

@bp.route('/supplier/receive/<int:order_id>', methods=['GET'])
@login_required
def supplier_receive_detail(order_id):
    if not current_user.is_staff():
         return redirect(url_for('main.index'))
         
    order = SupplyOrder.query.get_or_404(order_id)
    return render_template('admin/supplier/receive.html', order=order)

@bp.route('/supplier/update_payload/<int:item_id>', methods=['POST'])
@login_required
def supplier_update_payload(item_id):
    item = SupplyOrderItem.query.get_or_404(item_id)
    if item.order.status != 'placed':
        flash('Cannot update payload for this order.', 'danger')
        return redirect(url_for('main.supplier_receive_detail', order_id=item.order.id))
        
    action = request.form.get('action') 
    
    # Initialize payload if None
    if item.payload is None:
        item.payload = item.mass
        
    if action == 'increase':
        item.payload += 1
    elif action == 'decrease':
        if item.payload > 0:
            item.payload -= 1
            
    db.session.commit()
    return redirect(url_for('main.supplier_receive_detail', order_id=item.order.id))

@bp.route('/supplier/fusion/<int:order_id>', methods=['POST'])
@login_required
def supplier_fusion(order_id):
    order = SupplyOrder.query.get_or_404(order_id)
    if order.status != 'placed':
        flash('Order not ready for fusion.', 'danger')
        return redirect(url_for('main.supplier_receive_list'))
        
    # INVENTORY FUSION
    for item in order.items:

        qty_received = item.payload if item.payload is not None else item.mass
        
        # Update Book Stock
        item.book.stock_total += qty_received
        item.book.stock_available += qty_received
        
        # Update payload field for record keeping if it was None
        if item.payload is None:
            item.payload = qty_received
            
    order.status = 'completed'
    db.session.commit()
    
    flash('Inventory Fusion Complete! Stock updated.', 'success')
    return redirect(url_for('main.supplier_receive_list'))

@bp.route('/supplier/order/<int:order_id>', methods=['GET'])
@login_required
def supplier_order_detail(order_id):
    if not current_user.is_staff():
         return redirect(url_for('main.index'))
         
    order = SupplyOrder.query.get_or_404(order_id)
    return render_template('admin/supplier/order_detail.html', order=order)
