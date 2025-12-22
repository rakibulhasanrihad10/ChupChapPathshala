"""
Loan Service - Business logic for loan management.
Handles loan creation, returns, and status management.
"""

from datetime import datetime, timedelta
from app.models import Loan, Book, db
from flask import abort


class LoanService:
    """Service class for managing book loans."""
    
    DEFAULT_LOAN_PERIOD_DAYS = 14
    
    @staticmethod
    def return_loan(loan_id, user_id):
        """
        Process a book return.
        
        Args:
            loan_id: ID of the loan to return
            user_id: ID of the user returning the book
            
        Returns:
            Loan: The updated loan object
            
        Raises:
            PermissionError: If user doesn't own the loan
            ValueError: If loan is not active
        """
        loan = Loan.query.get_or_404(loan_id)
        
        # Validate ownership
        if loan.user_id != user_id:
            raise PermissionError("You are not allowed to return this book.")
        
        # Validate loan status
        if loan.status != 'active':
            raise ValueError("This loan has already been returned or closed.")
        
        # Update loan
        loan.return_date = datetime.utcnow()
        loan.status = 'returned'
        
        # Update book stock
        if loan.book:
            loan.book.stock_available += 1
            loan.book.stock_borrowed = max(0, loan.book.stock_borrowed - 1)
        
        db.session.commit()
        return loan
    
    @staticmethod
    def admin_return_loan(loan_id):
        """
        Process a book return by admin (no ownership check).
        
        Args:
            loan_id: ID of the loan to return
            
        Returns:
            Loan: The updated loan object
            
        Raises:
            ValueError: If loan is not active
        """
        loan = Loan.query.get_or_404(loan_id)
        
        # Validate loan status
        if loan.status != 'active':
            raise ValueError("Loan is already returned or invalid.")
        
        # Update loan
        loan.return_date = datetime.utcnow()
        loan.status = 'returned'
        
        # Update book stock
        if loan.book:
            loan.book.stock_available += 1
            loan.book.stock_borrowed = max(0, loan.book.stock_borrowed - 1)
        
        db.session.commit()
        return loan
    
    @staticmethod
    def create_loan(user_id, book_id, loan_period_days=None):
        """
        Create a new loan for a user.
        
        Args:
            user_id: ID of the user borrowing the book
            book_id: ID of the book to borrow
            loan_period_days: Number of days for the loan (default: 14)
            
        Returns:
            Loan: The created loan object
            
        Raises:
            ValueError: If book is not available
        """
        book = Book.query.get_or_404(book_id)
        
        # Check availability
        if book.stock_available <= 0:
            raise ValueError(f"Book '{book.title}' is not available for borrowing.")
        
        # Set loan period
        if loan_period_days is None:
            loan_period_days = LoanService.DEFAULT_LOAN_PERIOD_DAYS
        
        # Create loan
        loan = Loan(
            user_id=user_id,
            book_id=book_id,
            checkout_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=loan_period_days),
            status='active'
        )
        
        # Update book stock
        book.stock_available -= 1
        book.stock_borrowed += 1
        
        db.session.add(loan)
        db.session.commit()
        
        return loan
    
    @staticmethod
    def get_active_loans(user_id):
        """
        Get all active loans for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            list: List of active Loan objects
        """
        return Loan.query.filter_by(
            user_id=user_id,
            status='active'
        ).order_by(Loan.due_date.asc()).all()
    
    @staticmethod
    def get_overdue_loans(user_id=None):
        """
        Get overdue loans, optionally filtered by user.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            list: List of overdue Loan objects
        """
        query = Loan.query.filter(
            Loan.status == 'active',
            Loan.due_date < datetime.utcnow()
        )
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        return query.order_by(Loan.due_date.asc()).all()
    
    @staticmethod
    def calculate_days_remaining(loan):
        """
        Calculate days remaining for a loan.
        
        Args:
            loan: Loan object
            
        Returns:
            int: Days remaining (negative if overdue)
        """
        if loan.status != 'active':
            return 0
        
        delta = loan.due_date - datetime.utcnow()
        return delta.days
    
    @staticmethod
    def get_loan_history(user_id, status=None, page=1, per_page=10):
        """
        Get loan history for a user with pagination.
        
        Args:
            user_id: ID of the user
            status: Optional status filter ('active', 'returned', etc.)
            page: Page number
            per_page: Items per page
            
        Returns:
            Pagination: Paginated loan results
        """
        query = Loan.query.filter_by(user_id=user_id)
        
        if status:
            query = query.filter_by(status=status)
        
        return query.order_by(
            Loan.status.asc(),
            Loan.checkout_date.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
