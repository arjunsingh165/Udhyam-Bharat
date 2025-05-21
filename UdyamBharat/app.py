from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
import bcrypt
from datetime import datetime
from api import api
from chatbot import get_chatbot_response
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# MongoDB configuration
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.udyambharat

# Register API blueprint
app.register_blueprint(api)

# Flask-Login configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.email = user_data['email']
        self.role = user_data['role']
        self.name = user_data['name']

@login_manager.user_loader
def load_user(user_id):
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

def create_notification(user_id, message, type='order'):
    notification = {
        'user_id': user_id,
        'message': message,
        'type': type,
        'read': False,
        'created_at': datetime.utcnow()
    }
    db.notifications.insert_one(notification)

@app.route('/')
def index():
    # Get featured videos only
    videos = list(db.videos.find().limit(2))
    for video in videos:
        video['_id'] = str(video['_id'])
    
    return render_template('index.html', videos=videos)

@app.route('/select_role', methods=['POST'])
def select_role():
    role = request.form.get('role')
    if role in ['buyer', 'seller']:
        session['selected_role'] = role
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_data = db.users.find_one({'email': email})
        if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password']):
            user = User(user_data)
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = session.get('selected_role', 'buyer')
        
        if db.users.find_one({'email': email}):
            flash('Email already registered')
            return redirect(url_for('register'))
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_data = {
            'name': name,
            'email': email,
            'password': hashed_password,
            'role': role,
            'created_at': datetime.utcnow()
        }
        
        db.users.insert_one(user_data)
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'seller':
        products = list(db.products.find({'seller_id': current_user.id}))
        orders = list(db.orders.find({'seller_id': current_user.id}))
        jobs = list(db.jobs.find({'seller_id': current_user.id}))
        notifications = list(db.notifications.find({'user_id': current_user.id, 'read': False}))
        return render_template('seller_dashboard.html', products=products, orders=orders, jobs=jobs, notifications=notifications)
    else:
        orders = list(db.orders.find({'buyer_id': current_user.id}))
        notifications = list(db.notifications.find({'user_id': current_user.id, 'read': False}))
        return render_template('buyer_dashboard.html', products=[], orders=orders, notifications=notifications)

@app.route('/jobs')
@login_required
def jobs():
    if current_user.role != 'seller':
        flash('Only sellers can view job listings')
        return redirect(url_for('dashboard'))
    
    jobs = list(db.jobs.find())
    for job in jobs:
        job['_id'] = str(job['_id'])
        job['seller_id'] = str(job['seller_id'])
    return render_template('jobs.html', jobs=jobs)

@app.route('/jobs/post', methods=['GET', 'POST'])
@login_required
def post_job():
    if current_user.role != 'seller':
        flash('Only sellers can post jobs')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        job_data = {
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'location': request.form.get('location'),
            'seller_id': current_user.id,
            'created_at': datetime.utcnow()
        }
        db.jobs.insert_one(job_data)
        flash('Job posted successfully!')
        return redirect(url_for('jobs'))
    return render_template('post_job.html')

@app.route('/order_history')
@login_required
def order_history():
    if current_user.role == 'seller':
        orders = list(db.orders.find({'seller_id': current_user.id}))
    else:
        orders = list(db.orders.find({'buyer_id': current_user.id}))
    
    for order in orders:
        order['_id'] = str(order['_id'])
        order['product_id'] = str(order['product_id'])
        order['buyer_id'] = str(order['buyer_id'])
        order['seller_id'] = str(order['seller_id'])
        product = db.products.find_one({'_id': ObjectId(order['product_id'])})
        if product:
            order['product_name'] = product['name']
    
    return render_template('order_history.html', orders=orders)

@app.route('/notifications')
@login_required
def notifications():
    notifications = list(db.notifications.find({'user_id': current_user.id}).sort('created_at', -1))
    for notification in notifications:
        notification['_id'] = str(notification['_id'])
    return render_template('notifications.html', notifications=notifications)

@app.route('/notifications/mark_read/<notification_id>')
@login_required
def mark_notification_read(notification_id):
    db.notifications.update_one(
        {'_id': ObjectId(notification_id), 'user_id': current_user.id},
        {'$set': {'read': True}}
    )
    return redirect(url_for('notifications'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/buyer/dashboard')
@login_required
def buyer_dashboard():
    if current_user.role != 'buyer':
        return redirect(url_for('seller_dashboard'))
    
    # Don't show any products
    notifications = list(db.notifications.find({
        'user_id': current_user.id,
        'read': False
    }).sort('created_at', -1))
    
    return render_template('buyer_dashboard.html', 
                         products=[],
                         notifications=notifications)

@app.route('/api/cart', methods=['POST'])
@login_required
def add_to_cart():
    if current_user.role != 'buyer':
        return jsonify({'error': 'Only buyers can add items to cart'}), 403
    
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    # Validate product exists
    product = db.products.find_one({'_id': ObjectId(product_id)})
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    # Add to cart
    cart_item = {
        'user_id': current_user.id,
        'product_id': ObjectId(product_id),
        'quantity': quantity,
        'added_at': datetime.utcnow()
    }
    
    db.cart.update_one(
        {'user_id': current_user.id, 'product_id': ObjectId(product_id)},
        {'$set': cart_item},
        upsert=True
    )
    
    return jsonify({'message': 'Product added to cart'})

@app.route('/api/cart', methods=['GET'])
@login_required
def get_cart():
    if current_user.role != 'buyer':
        return jsonify({'error': 'Only buyers can view cart'}), 403
    
    cart_items = list(db.cart.find({'user_id': current_user.id}))
    
    # Get product details for each cart item
    for item in cart_items:
        product = db.products.find_one({'_id': item['product_id']})
        if product:
            item['product'] = {
                'name': product['name'],
                'price': product['price'],
                'image_url': product['image_url']
            }
    
    return jsonify(cart_items)

@app.route('/api/cart/<product_id>', methods=['DELETE'])
@login_required
def remove_from_cart(product_id):
    if current_user.role != 'buyer':
        return jsonify({'error': 'Only buyers can remove items from cart'}), 403
    
    result = db.cart.delete_one({
        'user_id': current_user.id,
        'product_id': ObjectId(product_id)
    })
    
    if result.deleted_count == 0:
        return jsonify({'error': 'Item not found in cart'}), 404
    
    return jsonify({'message': 'Item removed from cart'})

@app.route('/api/checkout', methods=['POST'])
@login_required
def checkout():
    if current_user.role != 'buyer':
        return jsonify({'error': 'Only buyers can checkout'}), 403
    
    # Get cart items
    cart_items = list(db.cart.find({'user_id': current_user.id}))
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400
    
    # Create orders for each item
    for item in cart_items:
        product = db.products.find_one({'_id': item['product_id']})
        if not product:
            continue
        
        order = {
            'buyer_id': current_user.id,
            'seller_id': product['seller_id'],
            'product_id': item['product_id'],
            'quantity': item['quantity'],
            'total_price': product['price'] * item['quantity'],
            'status': 'pending',
            'created_at': datetime.utcnow()
        }
        
        order_id = db.orders.insert_one(order).inserted_id
        
        # Create notification for seller
        notification = {
            'user_id': product['seller_id'],
            'message': f'New order received for {product["name"]}',
            'type': 'order',
            'order_id': order_id,
            'read': False,
            'created_at': datetime.utcnow()
        }
        db.notifications.insert_one(notification)
    
    # Clear cart
    db.cart.delete_many({'user_id': current_user.id})
    
    return jsonify({'message': 'Checkout successful'})

@app.route('/seller/dashboard')
@login_required
def seller_dashboard():
    if current_user.role != 'seller':
        return redirect(url_for('index'))
    
    # Only show seller's own products
    products = list(db.products.find({
        'seller_id': ObjectId(current_user.id)
    }))
    for product in products:
        product['_id'] = str(product['_id'])
        product['seller_id'] = str(product['seller_id'])
    
    # Fetch seller's jobs
    jobs = list(db.jobs.find({'seller_id': ObjectId(current_user.id)}))
    for job in jobs:
        job['_id'] = str(job['_id'])
        job['seller_id'] = str(job['seller_id'])
    
    # Fetch seller's orders
    orders = list(db.orders.find({'seller_id': ObjectId(current_user.id)}))
    for order in orders:
        order['_id'] = str(order['_id'])
        order['product_id'] = str(order['product_id'])
        order['buyer_id'] = str(order['buyer_id'])
        order['seller_id'] = str(order['seller_id'])
    
    return render_template('seller_dashboard.html', products=products, jobs=jobs, orders=orders)

@app.route('/api/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    response = get_chatbot_response(user_message)
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True) 