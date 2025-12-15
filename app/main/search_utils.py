from app.models import Book
from sqlalchemy import or_

def search_suggestions(query, limit=10):
    """
    Returns a list of book titles that match the query string.
    """
    if not query:
        return []
        
    # Case-insensitive LIKE query for SQLite - STARTS WITH only
    search_pattern = f"{query}%"
    books = Book.query.filter(Book.title.ilike(search_pattern))\
        .limit(50)\
        .all()
    
    # Python sorting - Alphabetical
    books.sort(key=lambda x: x.title.lower())
    
    # Return top 'limit' titles
    return [book.title for book in books[:limit]]

def full_text_search(query):
    """
    Returns a list of books matching the query in title or author.
    Ranked simply by exact match, then starts with, then contains.
    """
    if not query:
        return []

    search_pattern = f"%{query}%"
    
    
    books = Book.query.filter(
        or_(
            Book.title.ilike(search_pattern),
            Book.author.ilike(search_pattern)
        )
    ).all()


    
    query_lower = query.lower()
    
    def rank_score(book):
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
        
    # Sort by score descending
    books.sort(key=rank_score, reverse=True)
    
    return books
