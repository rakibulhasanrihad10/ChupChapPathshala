from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager, oauth, mail, back, socketio

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    login_manager.login_view = 'auth.login'
    oauth.init_app(app)
    
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url=app.config['GOOGLE_DISCOVERY_URL'],
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

    back.init_app(
        app,
        default_url="/",       # Where to go if nothing is saved
        use_referrer=True,             # Use Referer header as fallback
        excluded_endpoints=["static"]  # List of endpoints to skip
    )

    # Import models to register them with SQLAlchemy
    from app import models

    # Register Blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.forum import bp as forum_bp
    app.register_blueprint(forum_bp, url_prefix='/forum')


    from app.user import bp as user_bp
    app.register_blueprint(user_bp, url_prefix='/user')

    from app.chatbot import bp as chatbot_bp
    app.register_blueprint(chatbot_bp, url_prefix='/chatbot')

    from app.messages import bp as messages_bp
    app.register_blueprint(messages_bp, url_prefix='/messages')

    # Update last_seen timestamp on every request
    @app.before_request
    def before_request():
        from flask_login import current_user
        from datetime import datetime
        if current_user.is_authenticated:
            current_user.last_seen = datetime.utcnow()
            db.session.commit()

    # Initialize Socket.IO with Redis message queue
    socketio.init_app(
        app,
        message_queue=app.config.get('SOCKETIO_MESSAGE_QUEUE'),
        async_mode=app.config.get('SOCKETIO_ASYNC_MODE'),
        cors_allowed_origins=app.config.get('SOCKETIO_CORS_ALLOWED_ORIGINS'),
        logger=app.config.get('SOCKETIO_LOGGER', False),
        engineio_logger=app.config.get('SOCKETIO_ENGINEIO_LOGGER', False)
    )
    
    # Register Socket.IO events
    from app.messages import events

    return app

# Force reload for search ranking fix
