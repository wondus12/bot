# Main entry point for the Telegram bot
# Initializes the bot, loads handlers, and starts the polling/webhook

import logging
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from config import BOT_TOKEN, API_ID, API_HASH, ADMIN_IDS
from database import init_database
from handlers.command_handlers import (
    start_command, subscribe_command, status_command, help_command, button_callback
)
from handlers.content_handlers import (
    register_device_command, content_library_command, device_callback_handler
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Pyrogram client with proxy support
from pyrogram import enums

app = Client(
    "telegram_content_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    # Uncomment and configure if you have proxy:
    # proxy=dict(
    #     scheme="http",  # or "socks5"
    #     hostname="127.0.0.1",
    #     port=1080,
    #     username="username",  # optional
    #     password="password"   # optional
    # )
)

@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    """Handle /start command"""
    await start_command(client, message)

@app.on_message(filters.command("subscribe"))
async def subscribe_handler(client: Client, message: Message):
    """Handle /subscribe command"""
    await subscribe_command(client, message)

@app.on_message(filters.command("status"))
async def status_handler(client: Client, message: Message):
    """Handle /status command"""
    await status_command(client, message)

@app.on_message(filters.command("help"))
async def help_handler(client: Client, message: Message):
    """Handle /help command"""
    await help_command(client, message)

@app.on_message(filters.command("register_device"))
async def register_device_handler(client: Client, message: Message):
    """Handle /register_device command"""
    await register_device_command(client, message)

@app.on_message(filters.command("library"))
async def library_handler(client: Client, message: Message):
    """Handle /library command"""
    await content_library_command(client, message)

@app.on_callback_query()
async def callback_handler(client: Client, callback_query: CallbackQuery):
    """Handle callback queries"""
    # Route to appropriate handler based on callback data
    if callback_query.data.startswith(("view_plans", "select_plan_", "pay_chapa_", "about")):
        await button_callback(client, callback_query)
    else:
        await device_callback_handler(client, callback_query)

def main():
    """Start the bot."""
    # Initialize database
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    logger.info("Bot started successfully")
    
    # Run the bot
    app.run()

if __name__ == '__main__':
    main()