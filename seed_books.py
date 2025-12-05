from app import create_app, db
from app.models import Book
import random

app = create_app()
ctx = app.app_context()
ctx.push()

# Curated list of famous Bengali and Islamic books
books_data = [
    # Bengali Literature (Classics, Fiction, Poetry)
    {"title": "Gitanjali", "author": "Rabindranath Tagore", "category": "Bengali", "price": 250},
    {"title": "Shesher Kobita", "author": "Rabindranath Tagore", "category": "Bengali", "price": 200},
    {"title": "Pather Panchali", "author": "Bibhutibhushan Bandyopadhyay", "category": "Bengali", "price": 220},
    {"title": "Agnibina", "author": "Kazi Nazrul Islam", "category": "Bengali", "price": 180},
    {"title": "Devdas", "author": "Sarat Chandra Chattopadhyay", "category": "Bengali", "price": 150},
    {"title": "Putul Nacher Itikatha", "author": "Manik Bandyopadhyay", "category": "Bengali", "price": 210},
    {"title": "Lalsalu", "author": "Syed Waliullah", "category": "Bengali", "price": 160},
    {"title": "Chokher Bali", "author": "Rabindranath Tagore", "category": "Bengali", "price": 230},
    {"title": "Aranyak", "author": "Bibhutibhushan Bandyopadhyay", "category": "Bengali", "price": 240},
    {"title": "Padma Nadir Majhi", "author": "Manik Bandyopadhyay", "category": "Bengali", "price": 170},
    {"title": "Srikanta", "author": "Sarat Chandra Chattopadhyay", "category": "Bengali", "price": 260},
    {"title": "Feluda Samagra", "author": "Satyajit Ray", "category": "Bengali", "price": 500},
    {"title": "Byomkesh Samagra", "author": "Sharadindu Bandyopadhyay", "category": "Bengali", "price": 550},
    {"title": "Professor Shonku", "author": "Satyajit Ray", "category": "Bengali", "price": 300},
    {"title": "Hajar Bochor Dhore", "author": "Zahir Raihan", "category": "Bengali", "price": 190},
    {"title": "Dipu Number Two", "author": "Muhammed Zafar Iqbal", "category": "Bengali", "price": 200},
    {"title": "Ami Topu", "author": "Muhammed Zafar Iqbal", "category": "Bengali", "price": 180},
    {"title": "Ekattorer Dinguli", "author": "Jahanara Imam", "category": "Bengali", "price": 350},
    {"title": "Maa", "author": "Anisul Hoque", "category": "Bengali", "price": 280},
    {"title": "Nuruldiner Sara Jibon", "author": "Syed Shamsul Haq", "category": "Bengali", "price": 150},
    {"title": "Kabi", "author": "Tarashankar Bandyopadhyay", "category": "Bengali", "price": 220},
    {"title": "Himu Remand-e", "author": "Humayun Ahmed", "category": "Bengali", "price": 200},
    {"title": "Misir Ali", "author": "Humayun Ahmed", "category": "Bengali", "price": 250},
    {"title": "Shonkhonil Karagar", "author": "Humayun Ahmed", "category": "Bengali", "price": 180},
    {"title": "Jochna O Jononir Golpo", "author": "Humayun Ahmed", "category": "Bengali", "price": 450},

    # Islamic Books (Religion, History, Spirituality)
    {"title": "The Holy Quran (Bengali Translation)", "author": "Multiple", "category": "Islamic", "price": 600},
    {"title": "Sahih Al-Bukhari", "author": "Imam Bukhari", "category": "Islamic", "price": 1200},
    {"title": "Ar-Raheeq Al-Makhtum", "author": "Safiur Rahman Mubarakpuri", "category": "Islamic", "price": 400},
    {"title": "Riyad us-Saliheen", "author": "Imam An-Nawawi", "category": "Islamic", "price": 500},
    {"title": "Stories of the Prophets", "author": "Ibn Kathir", "category": "Islamic", "price": 350},
    {"title": "Tafsir Ibn Kathir", "author": "Ibn Kathir", "category": "Islamic", "price": 1500},
    {"title": "Don't Be Sad", "author": "Aaidh ibn Abdullah al-Qarni", "category": "Islamic", "price": 300},
    {"title": "Reclaim Your Heart", "author": "Yasmin Mogahed", "category": "Islamic", "price": 320},
    {"title": "Secrets of Divine Love", "author": "A. Helwa", "category": "Islamic", "price": 350},
    {"title": "Productive Muslim", "author": "Mohammed Faris", "category": "Islamic", "price": 280},
    {"title": "Lost Islamic History", "author": "Firas Alkhateeb", "category": "Islamic", "price": 300},
    {"title": "The Sealed Nectar", "author": "Safiur Rahman Mubarakpuri", "category": "Islamic", "price": 380},
    {"title": "Fortress of the Muslim", "author": "Said bin Ali bin Wahf Al-Qahtani", "category": "Islamic", "price": 100},
    {"title": "Road to Mecca", "author": "Muhammad Asad", "category": "Islamic", "price": 350},
    {"title": "Purification of the Heart", "author": "Hamza Yusuf", "category": "Islamic", "price": 250},
    {"title": "Agenda to Change Our Condition", "author": "Hamza Yusuf", "category": "Islamic", "price": 200},
    {"title": "Islam and the Destiny of Man", "author": "Charles Gai Eaton", "category": "Islamic", "price": 400},
    {"title": "Muhammad: His Life Based on the Earliest Sources", "author": "Martin Lings", "category": "Islamic", "price": 450},
    {"title": "In the Footsteps of the Prophet", "author": "Tariq Ramadan", "category": "Islamic", "price": 380},
    {"title": "Revival of Religious Sciences", "author": "Al-Ghazali", "category": "Islamic", "price": 800},
    
    # Children & Academic
    {"title": "Thakumar Jhuli", "author": "Dakshinaranjan Mitra Majumder", "category": "Children", "price": 150},
    {"title": "Gopal Bhar", "author": "Traditional", "category": "Children", "price": 120},
    {"title": "Chotoder Ramayana", "author": "Upendrakishore Ray Chowdhury", "category": "Children", "price": 180},
    {"title": "Tuntunir Boi", "author": "Upendrakishore Ray Chowdhury", "category": "Children", "price": 130},
    {"title": "Basic English Grammar", "author": "Betty Azar", "category": "Academic", "price": 250},
    {"title": "Physics for Dummies", "author": "Steven Holzner", "category": "Academic", "price": 300},
    {"title": "Introduction to Algorithms", "author": "Cormen et al.", "category": "Academic", "price": 800}
]

print(f"Starting seed process for {len(books_data)} books...")

added_count = 0
for data in books_data:
    # Check if book already exists
    exists = Book.query.filter_by(title=data['title']).first()
    if not exists:
        book = Book(
            title=data['title'],
            author=data['author'],
            category=data['category'],
            price=data['price'],
            item_type=random.choice(['sale', 'circulation', 'hybrid']),
            location=f"Aisle {random.randint(1,10)}, Shelf {random.choice(['A','B','C'])}",
            stock_total=random.randint(3, 10),
            stock_available=3 # Set a default
        )
        # Update available to match total
        book.stock_available = book.stock_total
        
        db.session.add(book)
        added_count += 1
        print(f"Added: {data['title']}")
    else:
        print(f"Skipped (Already exists): {data['title']}")

db.session.commit()
print(f"\nSuccess! Added {added_count} new books to the database.")
