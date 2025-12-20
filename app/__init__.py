from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager, oauth, mail, back

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


    return app

# Force reload for search ranking fix
