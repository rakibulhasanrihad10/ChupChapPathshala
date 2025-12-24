from app.models import Book, User, Loan, Sale, Supplier, SupplyOrder
from sqlalchemy import or_, and_, func
from datetime import datetime

def admin_search_suggestions(query, limit=10):
    """
    Returns mixed suggestions from books, members, orders, and suppliers.
    Each suggestion includes the text and type for display.
    """
    if not query or len(query) < 2:
        return []
    
    suggestions = []
    search_pattern = f"{query}%"
    contains_pattern = f"%{query}%"
    
    # Search Books (title and author)
    books = Book.query.filter(
        or_(
            Book.title.ilike(search_pattern),
            Book.author.ilike(search_pattern)
        )
    ).limit(3).all()
    
    for book in books:
        suggestions.append({
            'text': book.title,
            'type': 'book',
            'icon': 'fa-book',
            'id': book.id
        })
    
    # Search Members (username, email)
    members = User.query.filter(
        or_(
            User.username.ilike(search_pattern),
            User.email.ilike(contains_pattern)
        )
    ).limit(3).all()
    
    for member in members:
        suggestions.append({
            'text': f"{member.username} ({member.email})",
            'type': 'member',
            'icon': 'fa-user',
            'id': member.id,
            'username': member.username  # Add username for direct navigation
        })

    
    # Search Suppliers
    suppliers = Supplier.query.filter(
        or_(
            Supplier.name.ilike(search_pattern),
            Supplier.contact_person.ilike(search_pattern)
        )
    ).limit(2).all()
    
    for supplier in suppliers:
        suggestions.append({
            'text': supplier.name,
            'type': 'supplier',
            'icon': 'fa-truck',
            'id': supplier.id
        })
    
    # Limit total suggestions
    return suggestions[:limit]


def admin_full_search(query):
    """
    Returns comprehensive search results organized by category.
    """
    if not query:
        return {
            'books': [],
            'members': [],
            'loans': [],
            'sales': [],
            'suppliers': [],
            'supply_orders': []
        }
    
    search_pattern = f"%{query}%"
    query_lower = query.lower()
    
    # Search Books
    books = Book.query.filter(
        or_(
            Book.title.ilike(search_pattern),
            Book.author.ilike(search_pattern)
        )
    ).all()
    
    # Rank books
    def rank_book(book):
        title_lower = book.title.lower()
        author_lower = book.author.lower()
        if title_lower == query_lower:
            return 100
        if title_lower.startswith(query_lower):
            return 80
        if query_lower in title_lower:
            return 60
        if query_lower in author_lower:
            return 40
        return 0
    
    books.sort(key=rank_book, reverse=True)
    
    # Search Members
    members = User.query.filter(
        or_(
            User.username.ilike(search_pattern),
            User.email.ilike(search_pattern),
            User.phone_number.ilike(search_pattern)
        )
    ).all()
    
    # Search Loans (by user name or book title)
    loans = Loan.query.join(User).join(Book).filter(
        or_(
            User.username.ilike(search_pattern),
            Book.title.ilike(search_pattern),
            User.email.ilike(search_pattern)
        )
    ).order_by(Loan.checkout_date.desc()).limit(20).all()
    
    # Search Sales (by user name or book title)
    sales = Sale.query.join(User, Sale.user_id == User.id).join(Book, Sale.book_id == Book.id).filter(
        or_(
            User.username.ilike(search_pattern),
            Book.title.ilike(search_pattern),
            User.email.ilike(search_pattern)
        )
    ).order_by(Sale.sale_date.desc()).limit(20).all()
    
    # Search Suppliers
    suppliers = Supplier.query.filter(
        or_(
            Supplier.name.ilike(search_pattern),
            Supplier.contact_person.ilike(search_pattern),
            Supplier.email.ilike(search_pattern),
            Supplier.phone.ilike(search_pattern)
        )
    ).all()
    
    # Search Supply Orders (by supplier name)
    supply_orders = SupplyOrder.query.join(Supplier, SupplyOrder.supplier_id == Supplier.id, isouter=True).filter(
        or_(
            Supplier.name.ilike(search_pattern),
            SupplyOrder.status.ilike(search_pattern)
        )
    ).order_by(SupplyOrder.created_at.desc()).limit(20).all()
    
    return {
        'books': books,
        'members': members,
        'loans': loans,
        'sales': sales,
        'suppliers': suppliers,
        'supply_orders': supply_orders,
        'query': query
    }
