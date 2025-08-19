# Configuration settings loaded from environment variables
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID')) if os.getenv('API_ID') and os.getenv('API_ID').isdigit() else None
API_HASH = os.getenv('API_HASH') if os.getenv('API_HASH') != 'your_telegram_api_hash_here' else None
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot_database.db')
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

# Payment configuration
PAYMENT_PROVIDER_TOKEN = os.getenv('PAYMENT_PROVIDER_TOKEN')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET')
PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'sandbox')
CHAPA_SECRET_KEY = os.getenv('CHAPA_SECRET_KEY')
CHAPA_PUBLIC_KEY = os.getenv('CHAPA_PUBLIC_KEY')

# Webhook configuration
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://yourdomain.com/webhook')