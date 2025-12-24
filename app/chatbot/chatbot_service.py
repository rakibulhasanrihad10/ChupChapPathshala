import google.generativeai as genai
from flask import current_app
from app.models import Book, User, Loan, Cart, CartItem, Sale, Category
from app.extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import json

class ChatbotService:
    """Service class for handling chatbot interactions with Gemini API"""
    
    def __init__(self):
        self.model = None
        self.chat = None
        
    def initialize(self):
        """Initialize Gemini API with configuration"""
        api_key = current_app.config.get('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        
        genai.configure(api_key=api_key)
        model_name = current_app.config.get('GEMINI_MODEL', 'gemini-1.5-flash')
        
        # Define function declarations for Gemini
        tools = [
            {
                "function_declarations": [
                    {
                        "name": "search_books",
                        "description": "Search for books by title, author, or category. Returns a list of matching books with their details.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Search query for book title or author"
                                },
                                "category": {
                                    "type": "string",
                                    "description": "Optional category filter (e.g., Bengali, Islamic, Children, Academic)"
                                }
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "get_book_availability",
                        "description": "Check the availability and stock status of a specific book by its ID",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "book_id": {
                                    "type": "integer",
                                    "description": "The ID of the book to check"
                                }
                            },
                            "required": ["book_id"]
                        }
                    },
                    {
                        "name": "get_user_loans",
                        "description": "Get the list of books currently borrowed by a user, including due dates",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "user_id": {
                                    "type": "integer",
                                    "description": "The ID of the user"
                                }
                            },
                            "required": ["user_id"]
                        }
                    },
                    {
                        "name": "get_user_cart",
                        "description": "Get the items currently in a user's shopping cart",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "user_id": {
                                    "type": "integer",
                                    "description": "The ID of the user"
                                }
                            },
                            "required": ["user_id"]
                        }
                    },
                    {
                        "name": "get_low_stock_books",
                        "description": "Get books that are running low on stock (admin/staff only)",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "threshold": {
                                    "type": "integer",
                                    "description": "Stock threshold (default: 5)"
                                }
                            }
                        }
                    },
                    {
                        "name": "get_top_selling_books",
                        "description": "Get the top-selling books within a time period (admin/staff only)",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "limit": {
                                    "type": "integer",
                                    "description": "Number of books to return (default: 10)"
                                },
                                "days": {
                                    "type": "integer",
                                    "description": "Number of days to look back (default: 30)"
                                }
                            }
                        }
                    },
                    {
                        "name": "get_recommendations",
                        "description": "Get personalized book recommendations for a user based on their history and preferences",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "user_id": {
                                    "type": "integer",
                                    "description": "The ID of the user (optional for general recommendations)"
                                },
                                "category": {
                                    "type": "string",
                                    "description": "Optional category filter"
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Number of recommendations (default: 5)"
                                }
                            }
                        }
                    },
                    {
                        "name": "get_categories",
                        "description": "Get all available book categories",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ]
            }
        ]
        
        self.model = genai.GenerativeModel(
            model_name=model_name,
            tools=tools,
            system_instruction="""You are a helpful AI assistant for ChupChap Pathshala, a library management system. 
            You help users find books, check availability, manage their accounts, and provide recommendations.
            
            For staff and admin users, you can also help with inventory management and analytics.
            
            Be friendly, concise, and helpful. When presenting book information, format it nicely.
            If a user asks about their account (loans, cart), you'll need their user_id.
            If they're not logged in, politely inform them they need to log in first.
            
            Always be respectful and professional."""
        )

        
    def process_message(self, user_message, user_id=None, is_staff=False, conversation_history=None):
        """
        Process a user message and return a response
        
        Args:
            user_message: The user's message
            user_id: The ID of the logged-in user (None if anonymous)
            is_staff: Whether the user is staff/admin
            conversation_history: Previous messages in the conversation
            
        Returns:
            dict with 'response', 'intent', and 'metadata'
        """
        if not self.model:
            self.initialize()
        
        # Start or continue chat
        if conversation_history:
            # Convert history to Gemini format
            history = []
            for msg in conversation_history:
                history.append({"role": "user", "parts": [msg['message']]})
                history.append({"role": "model", "parts": [msg['response']]})
            self.chat = self.model.start_chat(history=history)
        else:
            self.chat = self.model.start_chat()
        
        # Add context about the user
        context = f"\n\nUser context: "
        if user_id:
            context += f"User ID: {user_id}, "
        if is_staff:
            context += "User is staff/admin with access to inventory and analytics features."
        else:
            context += "Regular customer user."
        
        # Send message
        response = self.chat.send_message(user_message + context)
        
        # Handle function calls
        intent = None
        metadata = {}
        
        while response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            
            # Check if there's a function call
            if hasattr(part, 'function_call') and part.function_call:
                function_call = part.function_call
                function_name = function_call.name
                function_args = dict(function_call.args)
                
                intent = function_name
                
                # Execute the function
                try:
                    result = self._execute_function(function_name, function_args, user_id, is_staff)
                    metadata[function_name] = result
                    
                    # Send function response back to model
                    response = self.chat.send_message(
                        genai.protos.Content(
                            parts=[genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=function_name,
                                    response={"result": result}
                                )
                            )]
                        )
                    )
                except Exception as e:
                    error_msg = f"Error executing {function_name}: {str(e)}"
                    response = self.chat.send_message(
                        genai.protos.Content(
                            parts=[genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=function_name,
                                    response={"error": error_msg}
                                )
                            )]
                        )
                    )
            else:
                # No more function calls, we have the final response
                break
        
        # Extract final text response
        final_response = response.text if response.text else "I'm sorry, I couldn't process that request."
        
        return {
            'response': final_response,
            'intent': intent,
            'metadata': metadata
        }
    
    def _execute_function(self, function_name, args, user_id, is_staff):
        """Execute a function call and return the result"""
        
        if function_name == "search_books":
            return self._search_books(args.get('query'), args.get('category'))
        
        elif function_name == "get_book_availability":
            return self._get_book_availability(args.get('book_id'))
        
        elif function_name == "get_user_loans":
            if not user_id:
                return {"error": "User must be logged in to view loans"}
            return self._get_user_loans(args.get('user_id', user_id))
        
        elif function_name == "get_user_cart":
            if not user_id:
                return {"error": "User must be logged in to view cart"}
            return self._get_user_cart(args.get('user_id', user_id))
        
        elif function_name == "get_low_stock_books":
            if not is_staff:
                return {"error": "This feature is only available to staff members"}
            return self._get_low_stock_books(args.get('threshold', 5))
        
        elif function_name == "get_top_selling_books":
            if not is_staff:
                return {"error": "This feature is only available to staff members"}
            return self._get_top_selling_books(args.get('limit', 10), args.get('days', 30))
        
        elif function_name == "get_recommendations":
            return self._get_recommendations(
                args.get('user_id', user_id),
                args.get('category'),
                args.get('limit', 5)
            )
        
        elif function_name == "get_categories":
            return self._get_categories()
        
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    def _search_books(self, query, category=None):
        """Search for books by title or author"""
        books_query = Book.query
        
        if category:
            books_query = books_query.filter(Book.category == category)
        
        if query:
            search_filter = db.or_(
                Book.title.ilike(f'%{query}%'),
                Book.author.ilike(f'%{query}%')
            )
            books_query = books_query.filter(search_filter)
        
        books = books_query.limit(10).all()
        
        return {
            "count": len(books),
            "books": [
                {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "category": book.category,
                    "price": book.price,
                    "sale_price": book.sale_price,
                    "discount": book.discount_percentage,
                    "available": book.stock_available,
                    "item_type": book.item_type
                }
                for book in books
            ]
        }
    
    def _get_book_availability(self, book_id):
        """Check availability of a specific book"""
        book = Book.query.get(book_id)
        
        if not book:
            return {"error": f"Book with ID {book_id} not found"}
        
        return {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "stock_total": book.stock_total,
            "stock_available": book.stock_available,
            "stock_borrowed": book.stock_borrowed,
            "stock_sold": book.stock_sold,
            "item_type": book.item_type,
            "is_available": book.stock_available > 0
        }
    
    def _get_user_loans(self, user_id):
        """Get user's active loans"""
        loans = Loan.query.filter_by(user_id=user_id, status='active').all()
        
        return {
            "count": len(loans),
            "loans": [
                {
                    "id": loan.id,
                    "book_title": loan.book.title,
                    "book_author": loan.book.author,
                    "checkout_date": loan.checkout_date.strftime('%Y-%m-%d'),
                    "due_date": loan.due_date.strftime('%Y-%m-%d') if loan.due_date else None,
                    "is_overdue": loan.due_date < datetime.utcnow() if loan.due_date else False
                }
                for loan in loans
            ]
        }
    
    def _get_user_cart(self, user_id):
        """Get user's cart items"""
        cart = Cart.query.filter_by(user_id=user_id).first()
        
        if not cart:
            return {"count": 0, "items": []}
        
        items = cart.items.all()
        
        return {
            "count": len(items),
            "items": [
                {
                    "book_title": item.book.title,
                    "book_author": item.book.author,
                    "quantity": item.quantity,
                    "action": item.action,
                    "price": item.book.sale_price
                }
                for item in items
            ]
        }
    
    def _get_low_stock_books(self, threshold):
        """Get books with low stock"""
        books = Book.query.filter(Book.stock_available <= threshold).all()
        
        return {
            "count": len(books),
            "threshold": threshold,
            "books": [
                {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "stock_available": book.stock_available,
                    "category": book.category
                }
                for book in books
            ]
        }
    
    def _get_top_selling_books(self, limit, days):
        """Get top-selling books"""
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Query sales grouped by book
        top_books = db.session.query(
            Book,
            func.count(Sale.id).label('sale_count')
        ).join(Sale).filter(
            Sale.sale_date >= since_date
        ).group_by(Book.id).order_by(
            desc('sale_count')
        ).limit(limit).all()
        
        return {
            "count": len(top_books),
            "period_days": days,
            "books": [
                {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "category": book.category,
                    "sales_count": sale_count,
                    "price": book.price
                }
                for book, sale_count in top_books
            ]
        }
    
    def _get_recommendations(self, user_id, category, limit):
        """Get book recommendations"""
        query = Book.query.filter(Book.stock_available > 0)
        
        if category:
            query = query.filter(Book.category == category)
        
        # If user is logged in, exclude books they already have
        if user_id:
            # Get books user has borrowed or bought
            borrowed_book_ids = db.session.query(Loan.book_id).filter_by(user_id=user_id).distinct()
            bought_book_ids = db.session.query(Sale.book_id).filter_by(user_id=user_id).distinct()
            
            query = query.filter(
                ~Book.id.in_(borrowed_book_ids),
                ~Book.id.in_(bought_book_ids)
            )
        
        # Get books with discounts first, then by popularity
        books = query.order_by(desc(Book.discount_percentage)).limit(limit).all()
        
        return {
            "count": len(books),
            "books": [
                {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "category": book.category,
                    "price": book.price,
                    "sale_price": book.sale_price,
                    "discount": book.discount_percentage
                }
                for book in books
            ]
        }
    
    def _get_categories(self):
        """Get all available categories"""
        categories = Category.query.all()
        
        # Also get categories from books if Category table is empty
        if not categories:
            book_categories = db.session.query(Book.category).distinct().all()
            return {
                "count": len(book_categories),
                "categories": [cat[0] for cat in book_categories if cat[0]]
            }
        
        return {
            "count": len(categories),
            "categories": [cat.name for cat in categories]
        }


chatbot_service = ChatbotService()
