# Simple script to run the bot
# This ensures proper environment setup before starting

import os
import sys
from pathlib import Path

def check_environment():
    """Check if environment is properly configured"""
    env_file = Path('.env')
    if not env_file.exists():
        print("ERROR: .env file not found!")
        print("Please copy .env.example to .env and configure your settings:")
        print("   - BOT_TOKEN (required)")
        print("   - CHAPA_SECRET_KEY and CHAPA_PUBLIC_KEY (for payments)")
        print("   - DATABASE_URL (defaults to SQLite)")
        return False
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("ERROR: BOT_TOKEN not set in .env file!")
        print("Get your bot token from @BotFather on Telegram")
        return False
    
    print("Environment configuration looks good!")
    return True

def main():
    """Main entry point"""
    print("Starting Telegram Content Bot...")
    
    if not check_environment():
        sys.exit(1)
    
    # Import and run the bot
    from bot import main as bot_main
    bot_main()

if __name__ == '__main__':
    main()
