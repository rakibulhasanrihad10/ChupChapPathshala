from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    admin = User.query.filter_by(email='admin@library.com').first()
    if admin:
        print(f"User: {admin.username}")
        print(f"Email: {admin.email}")
        print(f"Role: '{admin.role}'") # Quotes to see if empty or space
        
        all_admins = User.query.filter_by(role='admin').all()
        print(f"Total Admins found by query: {len(all_admins)}")
    else:
        print("User admin@library.com NOT FOUND")
