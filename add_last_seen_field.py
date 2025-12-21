from app import create_app, db
from app.models import User
from datetime import datetime

app = create_app()

with app.app_context():
    # Add last_seen column to users table
    with db.engine.connect() as conn:
        # Check if column exists (PostgreSQL)
        result = conn.execute(db.text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='last_seen'
        """))
        column_exists = result.fetchone() is not None
        
        if not column_exists:
            print("Adding last_seen column to users table...")
            conn.execute(db.text("ALTER TABLE users ADD COLUMN last_seen TIMESTAMP"))
            conn.commit()
            
            # Set default value for existing users
            print("Setting default last_seen for existing users...")
            conn.execute(db.text("UPDATE users SET last_seen = :now WHERE last_seen IS NULL"), 
                        {"now": datetime.utcnow()})
            conn.commit()
            
            print("✓ Migration completed successfully!")
        else:
            print("Column 'last_seen' already exists. Skipping migration.")
