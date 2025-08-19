# Handlers for callback queries and webhooks
# This file handles inline keyboard button presses and webhook events from payment providers

from telegram import Update
from telegram.ext import ContextTypes
import json
import logging
from config import CHAPA_SECRET_KEY, WEBHOOK_URL
from services.subscription_service import SubscriptionService
from services.payment_service import ChapaPaymentService
from models.user import User
from models.subscription_plan import SubscriptionPlan
from models.subscription import Subscription
from aiohttp import web

logger = logging.getLogger(__name__)

async def chapa_webhook_handler(request, session):
    """Handle Chapa webhook events"""
    try:
        # Extract payload
        payload = await request.json()
        
        # Log the incoming webhook
        logger.info(f"Chapa webhook received: {payload}")
        
        # Extract payment details
        transaction_id = payload.get('trx_ref') or payload.get('tx_ref')
        status = payload.get('status')
        
        # Verify webhook authenticity if Chapa provides signature verification
        # (Implementation depends on Chapa's specific webhook security features)
        
        if status == 'success' or status == 'completed':
            # Extract metadata
            metadata = payload.get('meta', {}) or payload.get('metadata', {})
            telegram_id = metadata.get('telegram_id')
            plan_id = metadata.get('plan_id')
            billing_cycle = metadata.get('billing_cycle')
            
            if telegram_id and plan_id:
                try:
                    # Create subscription
                    subscription = await SubscriptionService.create_subscription(
                        telegram_id, plan_id, transaction_id, session
                    )
                    
                    # Update payment status
                    subscription.payment_status = "completed"
                    session.commit()
                    
                    # Send confirmation to user via Telegram
                    # (This requires access to the bot instance)
                    # This might need to be implemented via a message queue or background task
                    
                    logger.info(f"Chapa payment processed successfully for user {telegram_id}")
                    return web.Response(status=200, text="OK")
                    
                except Exception as e:
                    logger.error(f"Error creating subscription for Chapa payment: {str(e)}")
                    # In a production environment, you might want to retry or alert on this
                    return web.Response(status=500, text="Error processing subscription")
            else:
                logger.warning("Chapa webhook missing required metadata")
                return web.Response(status=400, text="Missing required metadata")
        else:
            logger.info(f"Chapa payment not successful: {status}")
            return web.Response(status=200, text="Received")
        
    except Exception as e:
        logger.error(f"Error processing Chapa webhook: {str(e)}")
        return web.Response(status=500, text="Error processing webhook")