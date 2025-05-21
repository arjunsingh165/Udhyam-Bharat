from google import genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

def get_chatbot_response(user_message):
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_message,
        )
        # The response object has a .text attribute with the answer
        return {
            'success': True,
            'message': response.text
        }
    except Exception as e:
        print(f"Error in chatbot: {str(e)}")
        return {
            'success': False,
            'message': "I'm having trouble connecting. Please try again in a moment."
        } 