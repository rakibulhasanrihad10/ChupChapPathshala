from app.extensions import db
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import login_manager

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='customer')
    membership_type = db.Column(db.String(20), default='standard') # standard, premium
    membership_expiry = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_staff(self):
        return self.role in ['admin', 'librarian']

class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    author = db.Column(db.String(140), nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    # Inventory Management
    item_type = db.Column(db.String(20), default='hybrid') # circulation, sale, hybrid
    category = db.Column(db.String(50), default='General') # e.g. Fiction, Islamic, Bengali
    location = db.Column(db.String(100)) # e.g., "Aisle 3, Shelf B"
    image_url = db.Column(db.String(500), default='https://placehold.co/200x300?text=No+Cover') # Poster URL

    
    # Stock Counters
    stock_total = db.Column(db.Integer, default=1)
    stock_available = db.Column(db.Integer, default=1)
    stock_borrowed = db.Column(db.Integer, default=0)
    stock_sold = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Book {self.title}>'

class Cart(db.Model):
    __tablename__ = 'carts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', backref=db.backref('cart', uselist=False))
    items = db.relationship('CartItem', backref='cart', lazy='dynamic')

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('carts.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'))
    book = db.relationship('Book')
    quantity = db.Column(db.Integer, default=1)
    action = db.Column(db.String(20)) # 'borrow' or 'buy'

class Loan(db.Model):
    __tablename__ = 'loans'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'))
    checkout_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    return_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active') # active, returned, overdue

class Sale(db.Model):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'))
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    price_at_sale = db.Column(db.Float)

class Discount(db.Model):
    __tablename__ = 'discounts'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True)
    description = db.Column(db.String(100))
    discount_type = db.Column(db.String(20)) # 'percent', 'fixed'
    value = db.Column(db.Float)
    expiry_date = db.Column(db.DateTime)

    def is_valid(self):
        return self.expiry_date > datetime.utcnow()

class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    
    orders = db.relationship('SupplyOrder', backref='supplier', lazy='dynamic')

class SupplyOrder(db.Model):
    __tablename__ = 'supply_orders'
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True) # Nullable for draft/shortlist
    status = db.Column(db.String(20), default='shortlist') 
    # Statuses: 'shortlist', 'apply_gravity', 'pending_review', 'placed', 'completed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    items = db.relationship('SupplyOrderItem', backref='order', lazy='dynamic', cascade="all, delete-orphan")

class SupplyOrderItem(db.Model):
    __tablename__ = 'supply_order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('supply_orders.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'))
    book = db.relationship('Book')
    
    mass = db.Column(db.Integer, default=5) # Ordered Quantity
    payload = db.Column(db.Integer, nullable=True) # Received/Actual Quantity
