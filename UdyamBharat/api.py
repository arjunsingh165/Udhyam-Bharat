from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import os
from datetime import datetime
from flask_login import current_user, login_required
import assemblyai as aai
from elevenlabs.client import ElevenLabs
import requests
from werkzeug.utils import secure_filename

api = Blueprint('api', __name__)

# MongoDB configuration
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.udyambharat

# Configure API keys
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

@api.route('/api/products', methods=['GET'])
def get_products():
    category = request.args.get('category')
    district = request.args.get('district')
    query = {}
    
    if category:
        query['category'] = category
    if district:
        query['district'] = district
    
    products = list(db.products.find(query))
    for product in products:
        product['_id'] = str(product['_id'])
        product['seller_id'] = str(product['seller_id'])
    
    return jsonify(products)

@api.route('/api/products', methods=['POST'])
@login_required
def create_product():
    try:
        if current_user.role != 'seller':
            return jsonify({'error': 'Only sellers can create products'}), 403
        
        # Get form data with default values
        name = request.form.get('name', '')
        description = request.form.get('description', '')
        price = float(request.form.get('price', 0))
        district = request.form.get('district', '')
        image = request.files.get('image')
        
        if not image:
            return jsonify({'error': 'Product image is required'}), 400
        
        # Create product document
        product = {
            'name': name,
            'description': description,
            'price': price,
            'district': district,
            'seller_id': ObjectId(current_user.id),
            'seller_name': current_user.name,
            'created_at': datetime.utcnow()
        }
        
        # Handle image upload
        try:
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join('UdyamBharat', 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate secure filename with timestamp
            filename = secure_filename(f"{datetime.utcnow().timestamp()}_{image.filename}")
            image_path = os.path.join(upload_dir, filename)
            
            # Save the image
            image.save(image_path)
            
            # Set the image URL relative to static folder
            product['image_url'] = f'/static/uploads/{filename}'
        except Exception as e:
            print(f"Image upload error: {str(e)}")
            return jsonify({'error': 'Failed to upload image'}), 500
        
        # Save to database
        result = db.products.insert_one(product)
        
        # Convert ObjectId to string for JSON serialization
        product['_id'] = str(result.inserted_id)
        product['seller_id'] = str(product['seller_id'])
        
        return jsonify(product), 201
    
    except Exception as e:
        print(f"Product creation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/api/products/<product_id>', methods=['PUT'])
@login_required
def update_product(product_id):
    if current_user.role != 'seller':
        return jsonify({'error': 'Only sellers can update products'}), 403
    
    product = db.products.find_one({'_id': ObjectId(product_id)})
    if not product or str(product['seller_id']) != current_user.id:
        return jsonify({'error': 'Product not found'}), 404
    
    data = request.json
    update_data = {
        'name': data.get('name', product['name']),
        'description': data.get('description', product['description']),
        'price': float(data.get('price', product['price'])),
        'district': data.get('district', product['district'])
    }
    
    db.products.update_one({'_id': ObjectId(product_id)}, {'$set': update_data})
    return jsonify({'message': 'Product updated successfully'})

@api.route('/api/products/<product_id>', methods=['DELETE'])
@login_required
def delete_product(product_id):
    try:
        if current_user.role != 'seller':
            return jsonify({'error': 'Only sellers can delete products'}), 403
        
        # Find the product
        product = db.products.find_one({'_id': ObjectId(product_id)})
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Check if user is the product owner
        if str(product['seller_id']) != current_user.id:
            return jsonify({'error': 'You can only delete your own products'}), 403
        
        # Delete the product image if it exists and is not the default image
        if 'image_url' in product and product['image_url'] != '/static/images/default-product.jpg':
            try:
                image_path = os.path.join('UdyamBharat', product['image_url'].lstrip('/'))
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                print(f"Error deleting product image: {str(e)}")
        
        # Delete the product from database
        result = db.products.delete_one({'_id': ObjectId(product_id)})
        if result.deleted_count == 0:
            return jsonify({'error': 'Failed to delete product'}), 500
        
        return jsonify({'message': 'Product deleted successfully'}), 200
    
    except Exception as e:
        print(f"Product deletion error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/api/orders', methods=['GET'])
@login_required
def get_orders():
    if current_user.role == 'seller':
        orders = list(db.orders.find({'seller_id': current_user.id}))
    else:
        orders = list(db.orders.find({'buyer_id': current_user.id}))
    
    for order in orders:
        order['_id'] = str(order['_id'])
        order['product_id'] = str(order['product_id'])
        order['buyer_id'] = str(order['buyer_id'])
        order['seller_id'] = str(order['seller_id'])
    
    return jsonify(orders)

@api.route('/api/orders', methods=['POST'])
@login_required
def create_order():
    if current_user.role != 'buyer':
        return jsonify({'error': 'Only buyers can create orders'}), 403
    
    data = request.json
    product = db.products.find_one({'_id': ObjectId(data['product_id'])})
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    order = {
        'product_id': data['product_id'],
        'buyer_id': current_user.id,
        'seller_id': product['seller_id'],
        'quantity': int(data['quantity']),
        'status': 'pending',
        'created_at': datetime.utcnow()
    }
    
    result = db.orders.insert_one(order)
    order['_id'] = str(result.inserted_id)
    return jsonify(order), 201

@api.route('/api/orders/<order_id>', methods=['PUT'])
@login_required
def update_order_status(order_id):
    if current_user.role != 'seller':
        return jsonify({'error': 'Only sellers can update order status'}), 403
    
    data = request.json
    order = db.orders.find_one({'_id': ObjectId(order_id)})
    if not order or str(order['seller_id']) != current_user.id:
        return jsonify({'error': 'Order not found'}), 404
    
    db.orders.update_one(
        {'_id': ObjectId(order_id)},
        {'$set': {'status': data['status']}}
    )
    return jsonify({'message': 'Order status updated successfully'})

@api.route('/api/cart', methods=['GET'])
@login_required
def get_cart():
    if current_user.role != 'buyer':
        return jsonify({'error': 'Only buyers can access cart'}), 403
    
    cart = db.cart.find_one({'buyer_id': current_user.id})
    if not cart:
        return jsonify({'items': []})
    
    cart['_id'] = str(cart['_id'])
    cart['buyer_id'] = str(cart['buyer_id'])
    return jsonify(cart)

@api.route('/api/cart', methods=['POST'])
@login_required
def add_to_cart():
    if current_user.role != 'buyer':
        return jsonify({'error': 'Only buyers can add to cart'}), 403
    
    data = request.json
    product = db.products.find_one({'_id': ObjectId(data['product_id'])})
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    cart = db.cart.find_one({'buyer_id': current_user.id})
    if not cart:
        cart = {
            'buyer_id': current_user.id,
            'items': [{
                'product_id': data['product_id'],
                'quantity': int(data['quantity'])
            }]
        }
        db.cart.insert_one(cart)
    else:
        item_exists = False
        for item in cart['items']:
            if item['product_id'] == data['product_id']:
                item['quantity'] += int(data['quantity'])
                item_exists = True
                break
        
        if not item_exists:
            cart['items'].append({
                'product_id': data['product_id'],
                'quantity': int(data['quantity'])
            })
        
        db.cart.update_one(
            {'buyer_id': current_user.id},
            {'$set': {'items': cart['items']}}
        )
    
    return jsonify({'message': 'Item added to cart successfully'})

@api.route('/api/cart/<product_id>', methods=['DELETE'])
@login_required
def remove_from_cart(product_id):
    if current_user.role != 'buyer':
        return jsonify({'error': 'Only buyers can remove from cart'}), 403
    
    cart = db.cart.find_one({'buyer_id': current_user.id})
    if not cart:
        return jsonify({'error': 'Cart not found'}), 404
    
    cart['items'] = [item for item in cart['items'] if item['product_id'] != product_id]
    
    if not cart['items']:
        db.cart.delete_one({'buyer_id': current_user.id})
    else:
        db.cart.update_one(
            {'buyer_id': current_user.id},
            {'$set': {'items': cart['items']}}
        )
    
    return jsonify({'message': 'Item removed from cart successfully'})

@api.route('/api/voice/transcribe', methods=['POST'])
@login_required
def transcribe_voice():
    try:
        audio_file = request.files.get('audio')
        language = request.form.get('language', 'en')
        
        if not audio_file:
            return jsonify({'error': 'No audio file provided'}), 400
        
        # Map frontend language codes to AssemblyAI language codes
        language_map = {
            'en': 'en',
            'hi': 'hi',
            'doi': 'hi'  # Dogri uses Hindi as base language
        }
        
        assembly_language = language_map.get(language, 'en')
        
        # Save audio file temporarily
        filename = secure_filename(f"voice_input_{datetime.utcnow().timestamp()}.wav")
        filepath = os.path.join('static', 'temp', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        audio_file.save(filepath)
        
        # Configure transcription
        config = aai.TranscriptionConfig(
            language_code=assembly_language,
            punctuate=True,
            format_text=True,
            audio_format='wav'
        )
        
        # Create transcriber
        transcriber = aai.Transcriber(config=config)
        
        # Transcribe audio
        transcript = transcriber.transcribe(filepath)
        
        # Clean up temporary file
        try:
            os.remove(filepath)
        except:
            pass  # Ignore cleanup errors
        
        return jsonify({
            'transcript': transcript.text,
            'confidence': transcript.confidence,
            'language': language
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/api/voice/synthesize', methods=['POST'])
@login_required
def synthesize_voice():
    try:
        text = request.json.get('text')
        language = request.json.get('language', 'en')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Select voice based on language
        voice_map = {
            'en': 'Rachel',  # English voice
            'hi': 'Priya',   # Hindi voice
            'doi': 'Priya'   # Dogri voice (using Hindi voice as fallback)
        }
        voice = voice_map.get(language, 'Rachel')
        
        # Generate audio using ElevenLabs client
        audio = elevenlabs_client.generate(
            text=text,
            voice=voice,
            model="eleven_multilingual_v2"
        )
        
        # Save audio file
        filename = f'notification_{datetime.utcnow().timestamp()}.mp3'
        filepath = os.path.join('static', 'audio', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save the audio content
        with open(filepath, 'wb') as f:
            f.write(audio)
        
        return jsonify({'audio_url': f'/static/audio/{filename}'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/api/jobs/<job_id>', methods=['DELETE'])
@login_required
def delete_job(job_id):
    try:
        # Find the job
        job = db.jobs.find_one({'_id': ObjectId(job_id)})
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        # Check if user is the job poster
        if str(job['seller_id']) != current_user.id:
            return jsonify({'error': 'You can only delete your own jobs'}), 403
        
        # Delete the job
        result = db.jobs.delete_one({'_id': ObjectId(job_id)})
        if result.deleted_count == 0:
            return jsonify({'error': 'Failed to delete job'}), 500
        
        return jsonify({'message': 'Job deleted successfully'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500 