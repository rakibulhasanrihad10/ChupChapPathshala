import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, make_transient
from app import create_app
from app.extensions import db
from app.models import (
    User, Book, Cart, CartItem, Loan, Sale, Discount, 
    Supplier, SupplyOrder, SupplyOrderItem, EBook, 
    Campaign, Category, ForumPost, ForumComment
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def sync():
    # Source (Neon) URI from environment
    source_uri = os.environ.get('DATABASE_URL')
    if not source_uri:
        print("Error: DATABASE_URL not found in .env file.")
        return

    # Target (Local SQLite) URI
    target_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    target_uri = 'sqlite:///' + target_path

    print(f"Source: Neon (PostgreSQL)")
    print(f"Target: {target_path} (SQLite)")

    app = create_app()
    
    with app.app_context():
        # Create engines and sessions
        source_engine = create_engine(source_uri)
        SourceSession = sessionmaker(bind=source_engine)
        source_session = SourceSession()

        target_engine = create_engine(target_uri)
        TargetSession = sessionmaker(bind=target_engine)
        target_session = TargetSession()

        # Ensure target schema is created and matches models
        print("Recreating local database schema to match current models...")
        db.metadata.drop_all(target_engine)
        db.metadata.create_all(target_engine)

        # Tables in order to respect Foreign Key constraints
        models = [
            User,
            Category,
            Book,
            Supplier,
            Discount,
            Campaign,
            EBook,
            ForumPost,
            ForumComment,
            Cart,
            CartItem,
            Loan,
            Sale,
            SupplyOrder,
            SupplyOrderItem
        ]

        try:
            for model in models:
                table_name = model.__tablename__
                print(f"Syncing table: {table_name}...", end=" ", flush=True)
                
                # Clear existing data in target table
                target_session.query(model).delete()
                
                # Fetch all data from source
                items = source_session.query(model).all()
                
                if not items:
                    print("Empty (skipped)")
                    continue

                # Copy items to target
                for item in items:
                    source_session.expunge(item) # Detach from source session
                    make_transient(item)         # Make it look like a new object
                    target_session.add(item)     # Add to target session
                
                target_session.commit()
                print(f"Done ({len(items)} records)")

            print("\nSUCCESS: All data synchronized from Neon to app.db!")
            print("You can now test locally by commenting out DATABASE_URL in your .env file.")

        except Exception as e:
            target_session.rollback()
            print(f"\nERROR during synchronization: {str(e)}")
        finally:
            source_session.close()
            target_session.close()

if __name__ == "__main__":
    sync()
