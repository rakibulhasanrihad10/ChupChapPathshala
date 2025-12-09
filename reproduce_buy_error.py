from app import create_app, db
from app.models import User, Book, Cart, CartItem

def reproduce():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for testing client

    with app.test_client() as client:
        with app.app_context():
            # 1. Setup Data
            # Create a test customer
            user = User.query.filter_by(email='testcustomer@example.com').first()
            if not user:
                user = User(username='testcustomer', email='testcustomer@example.com', role='customer')
                user.set_password('password')
                db.session.add(user)
                db.session.commit()

            # Find a book that is 'sale' or 'hybrid'
            book = Book.query.filter(Book.item_type.in_(['sale', 'hybrid']), Book.stock_available > 0).first()
            if not book:
                print("No suitable book found for testing.")
                return

            print(f"Testing with Book ID: {book.id}, Title: {book.title}, Type: {book.item_type}")

            # 2. Login
            client.post('/auth/login', data={
                'email': 'testcustomer@example.com',
                'password': 'password'
            }, follow_redirects=True)

            # 3. Attempt to Buy
            response = client.post(f'/cart/add/{book.id}', data={'action': 'buy'}, follow_redirects=True)
            
            # 4. Check Result
            print(f"Response Status: {response.status_code}")
            decoded = response.data.decode('utf-8')
            
            # Check for Flash messages or Errors
            if "Added" in decoded and "to cart" in decoded:
                 print("SUCCESS: Item added to cart.")
            elif "danger" in decoded or "Error" in decoded:
                 print("FAILURE: Found error message in page.")
                 # Print snippet
                 start = decoded.find("alert-danger")
                 if start != -1:
                     print(decoded[start:start+200])
            else:
                 print("UNKNOWN RESULT. Printing text snippet:")
                 print(decoded[:500])

reproduce()
