from app.models import Book
from sqlalchemy import or_

def search_suggestions(query, limit=10):
    """
    Returns a list of book titles that match the query string.
    """
    if not query:
        return []
        
    # Case-insensitive LIKE query for SQLite
    search_pattern = f"%{query}%"
    books = Book.query.filter(Book.title.ilike(search_pattern))\
        .limit(limit)\
        .all()
        
    return [book.title for book in books]

def full_text_search(query):
    """
    Returns a list of books matching the query in title or author.
    Ranked simply by exact match, then starts with, then contains.
    """
    if not query:
        return []

    search_pattern = f"%{query}%"
    
    # In SQLite, we can't easily do complex ranking in one query without FTS extension efficiently configuration.
    # For this scale, we can fetch matching results and rank in Python or use ordering.
    
    # We will prioritize matches in Title over Author.
    # And we could try to prioritize 'starts with' over 'contains' using case expressions,
    # but simple filtering is usually enough for V1.
    
    books = Book.query.filter(
        or_(
            Book.title.ilike(search_pattern),
            Book.author.ilike(search_pattern)
        )
    ).all()
    
    # Simple Python ranking:
    # 1. Exact title match
    # 2. Title starts with query
    # 3. Title contains query
    # 4. Author matches
    
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
