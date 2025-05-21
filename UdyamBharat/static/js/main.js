// DOM Elements
const searchInput = document.getElementById('searchInput');
const categoryFilter = document.getElementById('categoryFilter');
const productsGrid = document.getElementById('productsGrid');
const cartItems = document.getElementById('cartItems');
const cartTotal = document.getElementById('cartTotal');
const checkoutButton = document.getElementById('checkoutButton');

// Cart Management
let cart = [];

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initializeVoiceInput();
    loadCart();
    setupEventListeners();
});

// Voice Input Setup
function initializeVoiceInput() {
    const voiceButtons = document.querySelectorAll('.voice-input');
    voiceButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const targetId = this.dataset.target;
            const targetInput = document.getElementById(targetId);
            const language = document.getElementById('voiceLanguage')?.value || 'en';
            
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const mediaRecorder = new MediaRecorder(stream, {
                    mimeType: 'audio/webm;codecs=opus'
                });
                const audioChunks = [];
                
                // Show recording status
                const statusDiv = document.createElement('div');
                statusDiv.className = 'recording-status mt-2 text-danger';
                statusDiv.textContent = 'Recording...';
                this.parentNode.appendChild(statusDiv);
                
                mediaRecorder.addEventListener('dataavailable', event => {
                    audioChunks.push(event.data);
                });
                
                mediaRecorder.addEventListener('stop', async () => {
                    statusDiv.textContent = 'Processing...';
                    statusDiv.className = 'recording-status mt-2 text-warning';
                    
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm;codecs=opus' });
                    const formData = new FormData();
                    formData.append('audio', audioBlob);
                    formData.append('language', language);
                    
                    try {
                        const response = await fetch('/api/voice/transcribe', {
                            method: 'POST',
                            body: formData
                        });
                        
                        if (!response.ok) {
                            throw new Error('Transcription failed');
                        }
                        
                        const data = await response.json();
                        if (data.transcript) {
                            targetInput.value = data.transcript;
                            // Trigger input event to ensure form validation
                            targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                            
                            statusDiv.textContent = `Transcribed (${Math.round(data.confidence * 100)}% confidence)`;
                            statusDiv.className = 'recording-status mt-2 text-success';
                            
                            // Remove status after 3 seconds
                            setTimeout(() => {
                                statusDiv.remove();
                            }, 3000);
                        } else {
                            throw new Error('No transcript received');
                        }
                    } catch (error) {
                        console.error('Transcription error:', error);
                        statusDiv.textContent = 'Transcription failed. Please try again.';
                        statusDiv.className = 'recording-status mt-2 text-danger';
                        
                        // Remove status after 3 seconds
                        setTimeout(() => {
                            statusDiv.remove();
                        }, 3000);
                    }
                });
                
                mediaRecorder.start();
                this.innerHTML = '<i class="bi bi-mic-fill"></i> Recording...';
                this.classList.add('btn-danger');
                
                setTimeout(() => {
                    mediaRecorder.stop();
                    stream.getTracks().forEach(track => track.stop());
                    this.innerHTML = '<i class="bi bi-mic"></i> Voice Input';
                    this.classList.remove('btn-danger');
                }, 5000);
            } catch (error) {
                console.error('Error accessing microphone:', error);
                alert('Could not access microphone. Please ensure you have granted microphone permissions.');
            }
        });
    });
}

// Event Listeners Setup
function setupEventListeners() {
    // Search functionality
    if (searchInput) {
        searchInput.addEventListener('input', debounce(handleSearch, 300));
    }
    
    // Category filter
    if (categoryFilter) {
        categoryFilter.addEventListener('change', handleSearch);
    }
    
    // Add to cart buttons
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', handleAddToCart);
    });
    
    // Checkout button
    if (checkoutButton) {
        checkoutButton.addEventListener('click', handleCheckout);
    }
}

// Search and Filter
function handleSearch() {
    const searchTerm = searchInput.value.toLowerCase();
    const category = categoryFilter.value;
    
    document.querySelectorAll('#productsGrid .col-md-4').forEach(card => {
        const title = card.querySelector('.card-title').textContent.toLowerCase();
        const description = card.querySelector('.card-text').textContent.toLowerCase();
        const productCategory = card.dataset.category;
        
        const matchesSearch = title.includes(searchTerm) || description.includes(searchTerm);
        const matchesCategory = !category || productCategory === category;
        
        card.style.display = matchesSearch && matchesCategory ? 'block' : 'none';
    });
}

// Cart Management
async function handleAddToCart(event) {
    const button = event.currentTarget;
    const productId = button.dataset.productId;
    const quantity = parseInt(button.parentElement.querySelector('input').value);
    
    try {
        const response = await fetch('/api/cart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                product_id: productId,
                quantity: quantity
            })
        });
        
        if (response.ok) {
            showNotification('Product added to cart!', 'success');
            loadCart();
        } else {
            const data = await response.json();
            showNotification(data.error || 'Error adding to cart', 'error');
        }
    } catch (error) {
        showNotification('Error adding to cart', 'error');
    }
}

async function loadCart() {
    try {
        const response = await fetch('/api/cart');
        if (response.ok) {
            const items = await response.json();
            updateCartDisplay(items);
        }
    } catch (error) {
        showNotification('Error loading cart', 'error');
    }
}

function updateCartDisplay(items) {
    if (!cartItems) return;
    
    cartItems.innerHTML = items.map(item => `
        <div class="cart-item">
            <img src="${item.product.image_url}" alt="${item.product.name}">
            <div class="cart-item-details">
                <h6>${item.product.name}</h6>
                <p>Quantity: ${item.quantity}</p>
                <p>Price: ₹${item.product.price * item.quantity}</p>
            </div>
            <button class="btn btn-sm btn-danger remove-item" data-product-id="${item.product_id}">
                <i class="bi bi-trash"></i>
            </button>
        </div>
    `).join('');
    
    const total = items.reduce((sum, item) => sum + (item.product.price * item.quantity), 0);
    cartTotal.textContent = total;
}

async function handleCheckout() {
    try {
        const response = await fetch('/api/checkout', {
            method: 'POST'
        });
        
        if (response.ok) {
            showNotification('Order placed successfully!', 'success');
            loadCart();
        } else {
            const data = await response.json();
            showNotification(data.error || 'Error during checkout', 'error');
        }
    } catch (error) {
        showNotification('Error during checkout', 'error');
    }
}

// Utility Functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} notification fade-in`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Quantity Controls
function incrementQuantity(button) {
    const input = button.parentElement.querySelector('input');
    const value = parseInt(input.value);
    if (value < 10) input.value = value + 1;
}

function decrementQuantity(button) {
    const input = button.parentElement.querySelector('input');
    const value = parseInt(input.value);
    if (value > 1) input.value = value - 1;
} 