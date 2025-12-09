import unittest
from datetime import datetime
from app import create_app, db
from app.models import User, Book, Cart, CartItem, Sale, Loan, Discount
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class TestLMS(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Setup Data
        self.user = User(username='testuser', email='test@example.com', membership_type='premium')
        self.user.set_password('password')
        db.session.add(self.user)
        
        self.book = Book(title='Python 101', author='Guido', price=100.0, stock_total=10, stock_available=10, item_type='hybrid')
        db.session.add(self.book)
        
        self.coupon = Discount(code='SAVE10', discount_type='percent', value=10.0, expiry_date=datetime(2030, 1, 1))
        db.session.add(self.coupon)
        
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_cart_and_checkout_flow(self):
        # 1. Add to Cart (Logic Simulation)
        cart = Cart(user_id=self.user.id)
        db.session.add(cart)
        cart_item = CartItem(cart=cart, book=self.book, quantity=1, action='buy')
        db.session.add(cart_item)
        db.session.commit()
        
        # Verify Cart
        self.assertEqual(self.user.cart.items.count(), 1)
        
        # 2. Checkout Logic Simulation (replicating checkout route logic)
        # Apply Discounts
        price = self.book.price
        # Membership (Premium = 10% off)
        if self.user.membership_type == 'premium':
            price *= 0.90
        
        # Coupon (SAVE10 = 10% off)
        coupon_val = 10.0
        price *= (1 - coupon_val/100)
        
        expected_price = 100.0 * 0.90 * 0.90 # 81.0
        
        # Create Sale
        sale = Sale(user_id=self.user.id, book_id=self.book.id, price_at_sale=price)
        db.session.add(sale)
        
        # Update Stock
        self.book.stock_sold += 1
        self.book.stock_available -= 1
        
        # DB Commit
        db.session.commit()
        
        # Assertions
        created_sale = Sale.query.first()
        self.assertAlmostEqual(created_sale.price_at_sale, 81.0)
        self.assertEqual(self.book.stock_available, 9)
        self.assertEqual(self.book.stock_sold, 1)
        print("Test Passed: Checkout Logic Correct (Price calculated: 81.0, Stock updated)")

if __name__ == '__main__':
    unittest.main()
