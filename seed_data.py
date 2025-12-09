from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # Create Admin User
    admin = User.query.filter_by(email='admin@library.com').first()
    if not admin:
        admin = User(username='admin', email='admin@library.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        print("Admin user created.")
    else:
        print("Admin user already exists.")

    # Create Staff User
    librarian = User.query.filter_by(email='librarian@library.com').first()
    if not librarian:
        librarian = User(username='librarian', email='librarian@library.com', role='librarian')
        librarian.set_password('librarian123')
        db.session.add(librarian)
        print("Librarian user created.")
    else:
        print("Librarian user already exists.")
        
    db.session.commit()
    print("Database seeded successfully.")
