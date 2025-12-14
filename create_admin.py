from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    user = User.query.filter_by(username='admin').first()
    if not user:
        user = User(username='admin', email='admin@example.com', role='admin')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        print("Admin user created")
    else:
        # Reset password to be sure
        user.set_password('password')
        db.session.commit()
        print("Admin user exists, password reset to 'password'")
