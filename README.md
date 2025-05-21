# UdyamBharat - Empowering Rural Artisans

UdyamBharat is a full-stack web application designed to connect rural artisans with potential buyers, providing a platform for showcasing and selling traditional handicrafts and products.

## Features

- User Authentication (Buyers and Sellers)
- Product Management
- Shopping Cart
- Order Processing
- Voice-based Notifications
- Job Posting and Application
- Real-time Chat
- Payment Integration
- Multi-language Support

## Tech Stack

- Backend: Python with Flask
- Database: MongoDB
- Frontend: HTML, CSS, JavaScript, Bootstrap
- Authentication: Flask-Login
- File Storage: Local Storage
- Voice Processing: AssemblyAI
- Text-to-Speech: ElevenLabs

## Prerequisites

- Python 3.8+
- MongoDB
- Virtual Environment (recommended)
- Git

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/UdyamBharat.git
cd UdyamBharat
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your actual values in `.env`
   - Never commit `.env` file to version control

Required environment variables:
```env
SECRET_KEY=your-secret-key
MONGODB_URI=your-mongodb-uri
MAIL_USERNAME=your-email
MAIL_PASSWORD=your-email-password
ASSEMBLYAI_API_KEY=your-assemblyai-key
ELEVENLABS_API_KEY=your-elevenlabs-key
GEMINI_API_KEY=your-gemini-key
```

5. Initialize the database:
```bash
python init_db.py
```

6. Run the application:
```bash
flask run
```

## Project Structure

```
UdyamBharat/
├── app.py              # Main application file
├── api.py             # API routes
├── config.py          # Configuration settings
├── init_db.py         # Database initialization
├── requirements.txt   # Project dependencies
├── static/           # Static files (CSS, JS, images)
├── templates/        # HTML templates
└── tests/           # Test files
```

## Security Notes

- All sensitive information is stored in environment variables
- Never commit `.env` file or any files containing API keys
- Passwords are hashed using bcrypt
- CSRF protection is enabled
- Rate limiting is implemented
- Secure session configuration is in place
- Input validation and sanitization is performed

## Testing

Run tests using pytest:
```bash
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

