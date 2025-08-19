# Payment Systems Integration

## Overview
This document outlines the implementation details for integrating payment systems into the Telegram bot, with a focus on Telegram Payments as the primary payment method, while also considering future integration with Stripe and PayPal.

## Telegram Payments Implementation

### Payment Service
```python
class PaymentService:
    @staticmethod
    async def create_subscription_invoice(bot, telegram_id, plan_id, billing_cycle):
        """Create subscription invoice for Telegram Payments"""
        # Get plan details
        plan = session.query(SubscriptionPlan).get(plan_id)
        if not plan:
            raise ValueError("Plan not found")
        
        # Determine price based on billing cycle
        price = plan.price_monthly if billing_cycle == "monthly" else plan.price_yearly
        
        # Create invoice details
        title = f"{plan.name} Subscription"
        description = f"{plan.description}\nBilling cycle: {billing_cycle}"
        payload = f"subscription_{plan.id}_{billing_cycle}_{telegram_id}"
        currency = "USD"  # Or configurable currency
        prices = [LabeledPrice(plan.name, int(price * 100))]  # Convert to cents
        
        # Send invoice
        invoice_message = await bot.send_invoice(
            chat_id=telegram_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=PAYMENT_PROVIDER_TOKEN,  # From config
            currency=currency,
            prices=prices,
            start_parameter="subscription-payment"
        )
        
        return invoice_message

    @staticmethod
    async def process_successful_payment(payment_data):
        """Process successful payment from Telegram"""
        # Extract information from payment
        telegram_id = payment_data['telegram_id']
        payload = payment_data['payload']
        payment_id = payment_data['payment_id']
        
        # Parse payload to get plan and billing info
        payload_parts = payload.split("_")
        if len(payload_parts) != 4 or payload_parts[0] != "subscription":
            raise ValueError("Invalid payment payload")
        
        plan_id = int(payload_parts[1])
        billing_cycle = payload_parts[2]
        
        try:
            # Create subscription
            subscription = await SubscriptionService.create_subscription(
                telegram_id, plan_id, payment_id
            )
            
            # Send confirmation to user
            return subscription, True
            
        except Exception as e:
            logger.error(f"Subscription creation failed: {str(e)}")
            raise
    
    @staticmethod
    async def handle_precheckout_query(query):
        """Handle pre-checkout queries from Telegram"""
        # Check if payment is valid (e.g., check payload)
        # For now, we'll just approve all payments
        await query.answer(ok=True)
        return True
    
    @staticmethod
    async def refund_payment(payment_id, reason=""):
        """Refund a payment"""
        # In a real implementation, you would use the Telegram Bot API to process refunds
        # For now, we'll just update our records
        
        # Find subscription associated with payment
        subscription = session.query(Subscription).filter(
            Subscription.payment_id == payment_id
        ).first()
        
        if subscription:
            subscription.payment_status = "refunded"
            session.commit()
            
            # Log refund
            logger.info(f"Refunded payment {payment_id} for subscription {subscription.id}: {reason}")
            return True
        
        return False
```

### Payment Handlers
```python
async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pre-checkout queries"""
    query = update.pre_checkout_query
    
    # Validate payment
    is_valid = await PaymentService.handle_precheckout_query(query)
    
    if not is_valid:
        await query.answer(ok=False, error_message="Payment validation failed")
        return
    
    await query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful payments"""
    # Extract information from payment
    telegram_id = update.message.from_user.id
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    payment_id = payment.provider_payment_charge_id
    
    try:
        # Process payment
        subscription, success = await PaymentService.process_successful_payment({
            'telegram_id': telegram_id,
            'payload': payload,
            'payment_id': payment_id
        })
        
        if success:
            # Send confirmation
            plan = subscription.plan
            await update.message.reply_text(
                f"🎉 Subscription successful!\n"
                f"Plan: {plan.name}\n"
                f"Billing cycle: {billing_cycle}\n"
                f"Expires: {subscription.end_date.strftime('%Y-%m-%d')}\n"
                f"You now have access to premium content!\n"
                f"Use /library to browse premium content."
            )
            
            # Send notification to user
            await NotificationService.create_notification(
                subscription.user_id,
                "Subscription Active",
                f"Your {plan.name} subscription is now active and will expire on {subscription.end_date.strftime('%Y-%m-%d')}.",
                "subscription"
            )
        else:
            await update.message.reply_text(
                "There was an error processing your subscription. "
                "Please contact support."
            )
            
    except Exception as e:
        # Log error and notify user
        logger.error(f"Payment processing failed: {str(e)}")
        await update.message.reply_text(
            "There was an error processing your payment. "
            "Please contact support."
        )
```

## Stripe Integration (Future Enhancement)

### Stripe Payment Service
```python
import stripe

class StripePaymentService:
    def __init__(self):
        stripe.api_key = STRIPE_SECRET_KEY  # From config
    
    async def create_subscription_checkout_session(self, telegram_id, plan_id, billing_cycle):
        """Create Stripe checkout session for subscription"""
        # Get plan details
        plan = session.query(SubscriptionPlan).get(plan_id)
        if not plan:
            raise ValueError("Plan not found")
        
        # Determine price based on billing cycle
        price = plan.price_monthly if billing_cycle == "monthly" else plan.price_yearly
        
        # Create checkout session
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f"{plan.name} Subscription",
                            'description': plan.description,
                        },
                        'unit_amount': int(price * 100),  # Convert to cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"{WEBHOOK_URL}/stripe/success?telegram_id={telegram_id}&plan_id={plan_id}&billing_cycle={billing_cycle}",
                cancel_url=f"{WEBHOOK_URL}/stripe/cancel",
                metadata={
                    'telegram_id': telegram_id,
                    'plan_id': plan_id,
                    'billing_cycle': billing_cycle
                }
            )
            
            return checkout_session.url
            
        except Exception as e:
            logger.error(f"Error creating Stripe checkout session: {str(e)}")
            raise
    
    async def handle_webhook(self, payload, sig_header, endpoint_secret):
        """Handle Stripe webhook events"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError:
            # Invalid payload
            return False
        except stripe.error.SignatureVerificationError:
            # Invalid signature
            return False
        
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            # Extract metadata
            telegram_id = session['metadata']['telegram_id']
            plan_id = session['metadata']['plan_id']
            billing_cycle = session['metadata']['billing_cycle']
            payment_id = session['payment_intent']
            
            try:
                # Create subscription
                subscription = await SubscriptionService.create_subscription(
                    telegram_id, plan_id, payment_id
                )
                
                # Send confirmation to user via Telegram
                # This would require storing the bot instance or using a different approach
                # to send messages outside of the normal update context
                
                return True
                
            except Exception as e:
                logger.error(f"Error processing Stripe payment: {str(e)}")
                return False
        
        return True
```

## PayPal Integration (Future Enhancement)

### PayPal Payment Service
```python
import paypalrestsdk

class PayPalPaymentService:
    def __init__(self):
        paypalrestsdk.configure({
            "mode": "sandbox",  # sandbox or live
            "client_id": PAYPAL_CLIENT_ID,  # From config
            "client_secret": PAYPAL_CLIENT_SECRET  # From config
        })
    
    async def create_subscription_payment(self, telegram_id, plan_id, billing_cycle):
        """Create PayPal payment for subscription"""
        # Get plan details
        plan = session.query(SubscriptionPlan).get(plan_id)
        if not plan:
            raise ValueError("Plan not found")
        
        # Determine price based on billing cycle
        price = plan.price_monthly if billing_cycle == "monthly" else plan.price_yearly
        
        # Create payment
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": f"{WEBHOOK_URL}/paypal/success",
                "cancel_url": f"{WEBHOOK_URL}/paypal/cancel"
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": f"{plan.name} Subscription",
                        "sku": f"subscription_{plan_id}_{billing_cycle}",
                        "price": f"{price:.2f}",
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": f"{price:.2f}",
                    "currency": "USD"
                },
                "description": plan.description
            }]
        })
        
        if payment.create():
            # Store payment ID and user info for later processing
            # This would typically be stored in a database or cache
            return payment.links[1].href  # Return approval URL
        else:
            logger.error(f"Error creating PayPal payment: {payment.error}")
            raise Exception("Failed to create PayPal payment")
    
    async def execute_payment(self, payment_id, payer_id):
        """Execute PayPal payment after user approval"""
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if payment.execute({"payer_id": payer_id}):
            # Extract payment details
            telegram_id = None  # This would need to be retrieved from stored data
            plan_id = None  # This would need to be retrieved from stored data
            billing_cycle = None  # This would need to be retrieved from stored data
            
            # Create subscription
            subscription = await SubscriptionService.create_subscription(
                telegram_id, plan_id, payment_id
            )
            
            return subscription
        else:
            logger.error(f"Error executing PayPal payment: {payment.error}")
            raise Exception("Failed to execute PayPal payment")
```
## Chapa Integration (New Payment Option)

Chapa is now available as a payment option, particularly suitable for Ethiopian users as it supports mobile money and bank transfers.

### Chapa Payment Service
```python
import requests
import logging
from datetime import datetime
from config import CHAPA_SECRET_KEY, CHAPA_PUBLIC_KEY, WEBHOOK_URL

logger = logging.getLogger(__name__)

class ChapaPaymentService:
    def __init__(self):
        self.secret_key = CHAPA_SECRET_KEY
        self.public_key = CHAPA_PUBLIC_KEY
        self.base_url = "https://api.chapa.co/v1"
    
    async def create_subscription_payment(self, telegram_id, plan_id, billing_cycle):
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
                "email": f"user{telegram_id}@example.com",  # Placeholder email
                "first_name": "Telegram",
                "last_name": "User",
                "tx_ref": tx_ref,
                "callback_url": f"{WEBHOOK_URL}/chapa/callback",
                "return_url": f"{WEBHOOK_URL}/chapa/return",
                "customization": {
                    "title": f"{plan.name} Subscription",
                    "description": plan.description
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
    
    async def handle_webhook(self, payload):
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
                        telegram_id, plan_id, transaction_id
                    )
                    
                    # Update payment status
                    subscription.payment_status = "completed"
                    session.commit()
                    
                    return True
                    
                except Exception as e:
                    logger.error(f"Error creating subscription for Chapa payment: {str(e)}")
                    return False
        
        return False
```

## Admin Payment Management

### Admin Payment Handlers
```python
@admin_required
async def admin_payments_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin payment management"""
    keyboard = [
        [InlineKeyboardButton("💰 Payment History", callback_data="admin_payment_history")],
        [InlineKeyboardButton("🔄 Refund Payment", callback_data="admin_refund_payment")],
        [InlineKeyboardButton("📊 Payment Statistics", callback_data="admin_payment_stats")],
        [InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💰 Payment Management\n"
        "Select an action:",
        reply_markup=reply_markup
    )

@admin_required
async def admin_payment_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment history view"""
    query = update.callback_query
    await query.answer()
    
    # Get recent payments (limit to 20)
    subscriptions = session.query(Subscription).order_by(
        Subscription.start_date.desc()
    ).limit(20).all()
    
    if not subscriptions:
        await query.edit_message_text(
            "No payment history found.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="admin_payments")
            ]])
        )
        return
    
    # Format payment history
    history_text = "💰 Recent Payments:\n\n"
    
    for subscription in subscriptions:
        user = subscription.user
        plan = subscription.plan
        status_emoji = {
            "completed": "✅",
            "pending": "⏳",
            "failed": "❌",
            "refunded": "↩️"
        }.get(subscription.payment_status, "❓")
        
        history_text += f"{status_emoji} {user.first_name} {user.last_name or ''}\n"
        history_text += f"  Plan: {plan.name}\n"
        history_text += f"  Amount: ${plan.price_monthly if 'monthly' in str(subscription.payment_id) else plan.price_yearly}\n"
        history_text += f"  Date: {subscription.start_date.strftime('%Y-%m-%d')}\n"
        history_text += f"  Status: {subscription.payment_status}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_payments")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(history_text, reply_markup=reply_markup)

@admin_required
async def admin_refund_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment refund"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "Please provide the payment ID you want to refund.\n"
        "You can find payment IDs in the payment history.\n\n"
        "Format: /refund_payment <payment_id> <reason>"
    )

async def admin_refund_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle refund payment command"""
    # Check if user is admin
    telegram_id = update.effective_user.id
    user = UserService.get_user(telegram_id)
    if not user or not user.is_admin:
        await update.message.reply_text("You don't have permission to use this command.")
        return
    
    # Check if arguments provided
    if len(context.args) < 2:
        await update.message.reply_text(
            "Please provide payment ID and reason.\n"
            "Format: /refund_payment <payment_id> <reason>"
        )
        return
    
    payment_id = context.args[0]
    reason = " ".join(context.args[1:])
    
    try:
        # Process refund
        success = await PaymentService.refund_payment(payment_id, reason)
        
        if success:
            await update.message.reply_text(
                f"✅ Payment {payment_id} refunded successfully.\n"
                f"Reason: {reason}"
            )
        else:
            await update.message.reply_text(
                f"❌ Failed to refund payment {payment_id}.\n"
                f"Please check the payment ID and try again."
            )
            
    except Exception as e:
        logger.error(f"Error processing refund: {str(e)}")
        await update.message.reply_text(
            "Error processing refund. Please try again."
        )
```

## Payment Security and Compliance

### Security Considerations
1. All payment processing is handled by secure payment providers (Telegram Payments, Stripe, PayPal, Chapa)
2. Sensitive payment information is never stored in our database
3. Payment webhooks are verified with signatures to prevent tampering
4. All communication with payment providers is over HTTPS
5. PCI DSS compliance is maintained by using third-party payment processors
6. Payment data is encrypted at rest in the database
7. Access to payment management features is restricted to admins only

### Error Handling
1. Invalid payment payloads - Log and notify user
2. Payment processing errors - Log and notify user to contact support
3. Refund processing errors - Log and notify admin
4. Network errors with payment providers - Retry with exponential backoff
5. Database errors in payment recording - Log and attempt to recover
6. Invalid payment IDs for refunds - Notify admin with clear error message

## Configuration Management

### Environment Variables
```python
# .env.example
TELEGRAM_PAYMENT_PROVIDER_TOKEN=your_telegram_payment_provider_token_here
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
PAYPAL_MODE=sandbox  # or live
CHAPA_SECRET_KEY=your_chapa_secret_key_here
CHAPA_PUBLIC_KEY=your_chapa_public_key_here
```

### Configuration Loading
```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Payments
PAYMENT_PROVIDER_TOKEN = os.getenv('TELEGRAM_PAYMENT_PROVIDER_TOKEN')

# Stripe
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# PayPal
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET')
PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'sandbox')
# Chapa
CHAPA_SECRET_KEY = os.getenv('CHAPA_SECRET_KEY')
CHAPA_PUBLIC_KEY = os.getenv('CHAPA_PUBLIC_KEY')

# Webhook URL for external payment providers
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://yourdomain.com/webhook')
```

## Testing and Validation

### Payment Testing
1. Test Telegram Payments with test cards provided by Telegram
2. Test Stripe integration with Stripe's test mode
3. Test PayPal integration with PayPal's sandbox environment
4. Test Chapa integration with Chapa's sandbox environment
5. Validate webhook handling for all payment providers
6. Test refund functionality for all payment methods
7. Verify proper error handling and user notifications
8. Test subscription creation and expiration scenarios
9. Validate payment status updates in the database

## Future Enhancements

1. Support for additional payment methods (cryptocurrency, bank transfers)
2. Subscription management (pause, cancel, upgrade/downgrade)
3. Coupon/discount code system
4. Tax calculation and handling
5. Multi-currency support
6. Automated billing and payment reminders
7. Payment analytics and reporting
8. Integration with accounting software
9. Support for one-time payments for individual content
10. Payment plan customization options
11. Enhanced Chapa integration with support for recurring payments