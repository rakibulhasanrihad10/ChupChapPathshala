"""
Cart Service - Business logic for shopping cart management.
Handles adding items, updating quantities, and cart operations.
"""

from app.models import Cart, CartItem, Book, db
from flask import abort


class CartService:
    """Service class for managing shopping cart operations."""
    
    @staticmethod
    def get_or_create_cart(user):
        """
        Get existing cart or create a new one for the user.
        
        Args:
            user: User object
            
        Returns:
            Cart: User's cart object
        """
        cart = user.cart
        if not cart:
            cart = Cart(user=user)
            db.session.add(cart)
            db.session.commit()
        return cart
    
    @staticmethod
    def add_item(user, book_id, action, quantity=1):
        """
        Add an item to the cart.
        
        Args:
            user: User object
            book_id: ID of the book to add
            action: 'borrow' or 'buy'
            quantity: Number of items to add (default: 1)
            
        Returns:
            tuple: (CartItem, bool) - The cart item and whether it was newly created
            
        Raises:
            ValueError: If action is invalid for the book type
        """
        book = Book.query.get_or_404(book_id)
        
        # Validate action against book type
        if action == 'borrow' and book.item_type == 'sale':
            raise ValueError('This item is for Sale only.')
        elif action == 'buy' and book.item_type == 'circulation':
            raise ValueError('This item is for Borrowing only.')
        
        # Get or create cart
        cart = CartService.get_or_create_cart(user)
        
        # Check if item already exists in cart
        cart_item = CartItem.query.filter_by(
            cart=cart,
            book=book,
            action=action
        ).first()
        
        if cart_item:
            # Update existing item
            cart_item.quantity += quantity
            created = False
        else:
            # Create new item
            cart_item = CartItem(
                cart=cart,
                book=book,
                quantity=quantity,
                action=action
            )
            db.session.add(cart_item)
            created = True
        
        db.session.commit()
        return cart_item, created
    
    @staticmethod
    def update_quantity(item_id, user, action):
        """
        Update the quantity of a cart item.
        
        Args:
            item_id: ID of the cart item
            user: User object (for authorization)
            action: 'increase' or 'decrease'
            
        Returns:
            CartItem: Updated cart item
            
        Raises:
            PermissionError: If user doesn't own the cart
            ValueError: If action is invalid or stock insufficient
        """
        item = CartItem.query.get_or_404(item_id)
        
        # Validate ownership
        if item.cart.user != user:
            raise PermissionError('Unauthorized access to cart item.')
        
        if action == 'increase':
            # Check stock for buying
            if item.action == 'buy' and item.book.stock_available <= item.quantity:
                raise ValueError('Not enough stock available.')
            item.quantity += 1
        elif action == 'decrease':
            if item.quantity > 1:
                item.quantity -= 1
            else:
                raise ValueError('Quantity cannot be less than 1. Use remove instead.')
        else:
            raise ValueError(f'Invalid action: {action}')
        
        db.session.commit()
        return item
    
    @staticmethod
    def remove_item(item_id, user):
        """
        Remove an item from the cart.
        
        Args:
            item_id: ID of the cart item to remove
            user: User object (for authorization)
            
        Raises:
            PermissionError: If user doesn't own the cart
        """
        item = CartItem.query.get_or_404(item_id)
        
        # Validate ownership
        if item.cart.user != user:
            raise PermissionError('Unauthorized access to cart item.')
        
        db.session.delete(item)
        db.session.commit()
    
    @staticmethod
    def get_cart_items(user):
        """
        Get all items in the user's cart.
        
        Args:
            user: User object
            
        Returns:
            list: List of CartItem objects
        """
        cart = user.cart
        if not cart:
            return []
        return cart.items.all()
    
    @staticmethod
    def calculate_subtotal(user):
        """
        Calculate the subtotal for items being purchased (not borrowed).
        
        Args:
            user: User object
            
        Returns:
            float: Subtotal amount
        """
        items = CartService.get_cart_items(user)
        subtotal = sum(
            item.book.sale_price * item.quantity 
            for item in items 
            if item.action == 'buy'
        )
        return subtotal
    
    @staticmethod
    def get_cart_count(user):
        """
        Get the total number of items in the cart.
        
        Args:
            user: User object
            
        Returns:
            int: Number of items in cart
        """
        cart = user.cart
        if not cart:
            return 0
        return cart.items.count()
    
    @staticmethod
    def clear_cart(user):
        """
        Remove all items from the user's cart.
        
        Args:
            user: User object
        """
        cart = user.cart
        if cart:
            CartItem.query.filter_by(cart_id=cart.id).delete()
            db.session.commit()
    
    @staticmethod
    def get_cart_summary(user):
        """
        Get a summary of the cart including items and totals.
        
        Args:
            user: User object
            
        Returns:
            dict: Cart summary with items, counts, and totals
        """
        items = CartService.get_cart_items(user)
        
        borrow_items = [item for item in items if item.action == 'borrow']
        buy_items = [item for item in items if item.action == 'buy']
        
        subtotal = sum(item.book.sale_price * item.quantity for item in buy_items)
        
        return {
            'items': items,
            'borrow_items': borrow_items,
            'buy_items': buy_items,
            'total_items': len(items),
            'borrow_count': len(borrow_items),
            'buy_count': len(buy_items),
            'subtotal': subtotal
        }
    
    @staticmethod
    def validate_cart_for_checkout(user):
        """
        Validate that the cart is ready for checkout.
        
        Args:
            user: User object
            
        Returns:
            tuple: (bool, str) - (is_valid, error_message)
        """
        items = CartService.get_cart_items(user)
        
        if not items:
            return False, 'Cart is empty.'
        
        # Check stock availability for buy items
        for item in items:
            if item.action == 'buy':
                if item.book.stock_available < item.quantity:
                    return False, f'Insufficient stock for "{item.book.title}".'
        
        return True, None
