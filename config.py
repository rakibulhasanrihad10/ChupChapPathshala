import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    APPROVED_ADMIN_DOMAINS = ['@gmail.com']
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
    GOOGLE_DISCOVERY_URL = (
        "https://accounts.google.com/.well-known/openid-configuration"
    )
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app/static/uploads/covers')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB Limit

    # Email Config
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 8025) 
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = [os.environ.get('MAIL_USERNAME') or 'your-email@example.com']
    
    # Gemini AI Chatbot Config
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL') or 'gemini-flash-latest'
    
    # Redis and Socket.IO Config
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    SOCKETIO_MESSAGE_QUEUE = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    SOCKETIO_ASYNC_MODE = 'threading'  # Changed from 'eventlet' for Python 3.13 compatibility
    SOCKETIO_CORS_ALLOWED_ORIGINS = '*'  # Configure appropriately for production

