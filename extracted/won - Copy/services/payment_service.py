# Payment processing logic
# Telegram Payments integration, payment status management, etc.

import requests
import logging
from datetime import datetime
from config import CHAPA_SECRET_KEY, CHAPA_PUBLIC_KEY, WEBHOOK_URL
from models.subscription_plan import SubscriptionPlan
from services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

class ChapaPaymentService:
    def __init__(self):
        self.secret_key = CHAPA_SECRET_KEY
        self.public_key = CHAPA_PUBLIC_KEY
        self.base_url = "https://api.chapa.co/v1"
    
    async def create_subscription_payment(self, telegram_id, plan_id, billing_cycle, session):
        """Create Chapa payment for subscription"""
        # Get plan details
        plan = session.query(SubscriptionPlan).get(plan_id)
        if not plan:
            raise ValueError("Plan not found")
        
        # Determine price based on billing cycle
        price = plan.price_monthly if billing_cycle == "monthly" else plan.price_yearly
        
        # Generate unique transaction reference
        tx_ref = f"subscription_{plan.id}_{billing_cycle}_{telegram_id}_{int(datetime.utcnow().timestamp())}"
        
        # Create Chapa payment
        try:
            # Chapa payment data
            payment_data = {
                "amount": str(price),
                "currency": "ETB",  # Ethiopian Birr
                "email": f"user{telegram_id}@bot.com",  # Valid email format
                "first_name": "Bot",
                "last_name": "User",
                "tx_ref": tx_ref,
                "callback_url": f"{WEBHOOK_URL}/chapa/callback",
                "return_url": f"{WEBHOOK_URL}/chapa/return",
                "customization": {
                    "title": plan.name[:16],  # Limit to 16 characters
                    "description": plan.description[:50] if plan.description else "Subscription"
                },
                "metadata": {
                    "telegram_id": telegram_id,
                    "plan_id": plan_id,
                    "billing_cycle": billing_cycle
                }
            }
            
            # Make request to Chapa API to create payment
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.base_url}/transaction/initialize",
                json=payment_data,
                headers=headers
            )
            
            response_data = response.json()
            
            if response_data.get("status") == "success":
                return response_data.get("data", {}).get("checkout_url")
            else:
                raise Exception(f"Chapa payment creation failed: {response_data.get('message')}")
            
        except Exception as e:
            logger.error(f"Error creating Chapa payment: {str(e)}")
            raise
    
    async def verify_payment(self, transaction_id):
        """Verify Chapa payment"""
        try:
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.base_url}/transaction/verify/{transaction_id}",
                headers=headers
            )
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error verifying Chapa payment: {str(e)}")
            raise
    
    async def handle_webhook(self, payload, session):
        """Handle Chapa webhook events"""
        # Process payment confirmation
        transaction_id = payload.get('trx_ref')
        status = payload.get('status')
        
        if status == 'success':
            # Extract metadata
            metadata = payload.get('meta', {})
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
                    
                    return True
                    
                except Exception as e:
                    logger.error(f"Error creating subscription for Chapa payment: {str(e)}")
                    return False
        
        return False

# Also include the existing Telegram PaymentService for completeness
class PaymentService:
    @staticmethod
    async def create_subscription_invoice(bot, telegram_id, plan_id, billing_cycle):
        """Create subscription invoice for Telegram Payments"""
        # Implementation would go here
        pass
    
    @staticmethod
    async def process_successful_payment(payment_data):
        """Process successful payment from Telegram"""
        # Implementation would go here
        pass
    
    @staticmethod
    async def handle_precheckout_query(query):
        """Handle pre-checkout queries from Telegram"""
        # Implementation would go here
        pass
    
    @staticmethod
    async def refund_payment(payment_id, reason=""):
        """Refund a payment"""
        # Implementation would go here
        pass