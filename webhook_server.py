# Webhook server for handling payment callbacks
from aiohttp import web, ClientSession
import json
import logging
from database import SessionLocal
from handlers.callback_handler import chapa_webhook_handler
from config import WEBHOOK_URL

logger = logging.getLogger(__name__)

async def chapa_webhook_endpoint(request):
    """Handle Chapa webhook callbacks"""
    session = SessionLocal()
    try:
        return await chapa_webhook_handler(request, session)
    finally:
        session.close()

async def health_check(request):
    """Health check endpoint"""
    return web.Response(text="OK", status=200)

def create_app():
    """Create webhook server application"""
    app = web.Application()
    
    # Add routes
    app.router.add_post('/chapa/callback', chapa_webhook_endpoint)
    app.router.add_get('/health', health_check)
    
    return app

if __name__ == '__main__':
    app = create_app()
    web.run_app(app, host='0.0.0.0', port=8080)
