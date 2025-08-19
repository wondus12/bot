#!/usr/bin/env python3
"""
Simple test script to verify bot token and basic connectivity
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

def test_bot_token():
    """Test if bot token is valid using Telegram Bot API"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['ok']:
                bot_info = data['result']
                print("Bot token is valid!")
                print(f"Bot name: {bot_info['first_name']}")
                print(f"Bot username: @{bot_info['username']}")
                print(f"Bot ID: {bot_info['id']}")
                return True
            else:
                print("Bot token is invalid!")
                return False
        else:
            print(f"HTTP Error: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return False

if __name__ == "__main__":
    print("Testing bot token connectivity...")
    test_bot_token()
