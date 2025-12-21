from app import create_app, db
from app.models import Message

app = create_app()

with app.app_context():
    db.create_all()
    print("Database tables updated (Message table created if not exists).")
