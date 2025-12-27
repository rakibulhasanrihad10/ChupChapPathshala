from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_back import Back
from flask_socketio import SocketIO

from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
oauth = OAuth()
mail = Mail()
back = Back()
socketio = SocketIO()
