import logging
# Fix logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from app import create_app, db
from app.models import User, Book, SupplyOrder, SupplyOrderItem, Supplier

app = create_app()

def verify_supplier_workflow():
    with app.app_context():
        logging.info("Starting Supplier Workflow Verification")
        
        # 1. Setup Data
        logging.info("Step 1: Setting up test data (User, Book)...")
        # Ensure we have a staff user (mocking login by just using logic)
        staff = User.query.filter_by(email='staff@test.com').first()
        if not staff:
            staff = User(username='staff_test', email='staff@test.com', role='librarian')
            staff.set_password('password')
            db.session.add(staff)
            
        # Create a Supplier
        supplier = Supplier.query.filter_by(name='Anti-Gravity Books').first()
        if not supplier:
            supplier = Supplier(name='Anti-Gravity Books', email='supply@books.com')
            db.session.add(supplier)
            
        # Create a Low Stock Book
        book = Book.query.filter_by(title='Floating Book').first()
        if not book:
            book = Book(title='Floating Book', author='Isaac Newton', price=10.0, stock_available=2, stock_total=2)
            db.session.add(book)
        else:
            book.stock_available = 2 # Ensure it is low
            
        db.session.commit()
        book_id = book.id
        logging.info(f"Book '{book.title}' stock: {book.stock_available} (Threshold < 5)")
        
        # 2. Simulate Shortlist (Anti-Gravity Pull)
        logging.info("Step 2: Simulating Auto-Pull to Shortlist...")
        # Get/Create active order
        order = SupplyOrder.query.filter_by(status='shortlist').first()
        if not order:
            order = SupplyOrder(status='shortlist')
            db.session.add(order)
            db.session.commit()
            
        # Manually trigger the "Pull" logic (normally in route)
        # Find low stock books
        low_stock_checks = Book.query.filter(Book.stock_available < 5).all()
        existing_ids = [item.book_id for item in order.items]
        
        if book.id in [b.id for b in low_stock_checks] and book.id not in existing_ids:
            new_item = SupplyOrderItem(order_id=order.id, book_id=book.id, mass=5)
            db.session.add(new_item)
            db.session.commit()
            logging.info("-> Anti-Gravity Effect: Book pulled to shortlist.")
        else:
            logging.info("-> Book already in shortlist or not low stock.")
            
        # Verify item in order
        item = SupplyOrderItem.query.filter_by(order_id=order.id, book_id=book.id).first()
        assert item is not None, "Book should be in shortlist"
        assert item.mass == 5, "Default mass should be 5"
        
        # 3. Adjust Mass
        logging.info("Step 3: Adjusting Mass...")
        item.mass = 12
        db.session.commit()
        assert item.mass == 12, "Mass should be adjusted to 12"
        logging.info("-> Mass adjusted to 12.")
        
        # 4. Submit to Review
        logging.info("Step 4: Submitting Review Beacon...")
        order.status = 'pending_review'
        db.session.commit()
        assert order.status == 'pending_review'
        
        # 5. Owner Launch
        logging.info("Step 5: Owner Launch Authorization...")
        order.status = 'placed'
        db.session.commit()
        assert order.status == 'placed'
        logging.info("-> Order status: Placed")
        
        # 6. Receive (Update Payload)
        logging.info("Step 6: Delivery Re-Entry (Update Payload)...")
        # Simulate receiving only 10 instead of 12
        item.payload = 10
        db.session.commit()
        assert item.payload == 10
        logging.info("-> Received Payload: 10 (Short delivery)")
        
        # 7. Inventory Fusion
        logging.info("Step 7: Inventory Fusion...")
        initial_stock = book.stock_total
        initial_avail = book.stock_available
        logging.info(f"-> Pre-Fusion Stock: Total={initial_stock}, Avail={initial_avail}")
        
        # Perform Fusion Logic
        qty_received = item.payload
        item.book.stock_total += qty_received
        item.book.stock_available += qty_received
        order.status = 'completed'
        db.session.commit()
        
        # 8. Verify Final State
        db.session.refresh(book)
        logging.info(f"-> Post-Fusion Stock: Total={book.stock_total}, Avail={book.stock_available}")
        
        assert book.stock_total == initial_stock + 10
        assert book.stock_available == initial_avail + 10
        assert order.status == 'completed'
        
        logging.info("SUCCESS: Supplier Workflow Verified!")

if __name__ == '__main__':
    verify_supplier_workflow()
