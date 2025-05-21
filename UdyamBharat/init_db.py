from pymongo import MongoClient, ASCENDING, TEXT
from config import Config
import os

def init_db():
    # Connect to MongoDB
    client = MongoClient(Config.MONGODB_URI)
    db = client[Config.MONGODB_DB]
    
    # Create collections if they don't exist
    collections = ['users', 'products', 'orders', 'cart', 'jobs', 'notifications', 'videos']
    for collection in collections:
        if collection not in db.list_collection_names():
            db.create_collection(collection)
    
    # Create indexes
    # Users collection
    db.users.create_index([('email', ASCENDING)], unique=True)
    db.users.create_index([('role', ASCENDING)])
    
    # Products collection
    db.products.create_index([('seller_id', ASCENDING)])
    db.products.create_index([('category', ASCENDING)])
    db.products.create_index([('district', ASCENDING)])
    db.products.create_index([
        ('name', TEXT),
        ('description', TEXT)
    ])
    
    # Orders collection
    db.orders.create_index([('user_id', ASCENDING)])
    db.orders.create_index([('seller_id', ASCENDING)])
    db.orders.create_index([('status', ASCENDING)])
    
    # Cart collection
    db.cart.create_index([('user_id', ASCENDING)])
    db.cart.create_index([('product_id', ASCENDING)])
    
    # Jobs collection
    db.jobs.create_index([('seller_id', ASCENDING)])
    db.jobs.create_index([('location', ASCENDING)])
    db.jobs.create_index([
        ('title', TEXT),
        ('description', TEXT)
    ])
    
    # Notifications collection
    db.notifications.create_index([('user_id', 1), ('read', 1)])
    db.notifications.create_index('created_at')
    
    # Videos collection
    db.videos.create_index('title')
    db.videos.create_index('category')
    
    # Create necessary directories
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.NOTIFICATION_AUDIO_FOLDER, exist_ok=True)
    os.makedirs('static/uploads', exist_ok=True)
    os.makedirs('static/videos', exist_ok=True)
    os.makedirs('static/notifications', exist_ok=True)
    
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_db() 