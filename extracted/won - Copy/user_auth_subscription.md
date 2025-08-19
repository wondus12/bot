# User Authentication and Subscription Management Implementation

## Overview
This document outlines the implementation details for user authentication and subscription management in the Telegram bot. These are core features that enable user registration, login, and subscription handling.

## Required Imports
```python
from payment_systems import ChapaPaymentService  # For Chapa payment integration
```

## User Authentication

### Registration Process
1. User initiates registration with `/register` command
2. Bot checks if user already exists in database
3. If user exists, send message that they're already registered
4. If user doesn't exist:
   - Collect user information from Telegram (ID, username, first name, last name)
   - Create new user record in database
   - Set initial user status (is_active=True, is_admin=False)
   - Send welcome message with profile details

### User Model Structure
```python
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    registration_date = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="user")
    interactions = relationship("UserInteraction", back_populates="user")
    referrals = relationship("Referral", foreign_keys="[Referral.referrer_id]", back_populates="referrer")
    referred_by = relationship("Referral", foreign_keys="[Referral.referred_id]", back_populates="referred")
    notifications = relationship("Notification", back_populates="user")
```

### Authentication Service
```python
class UserService:
    @staticmethod
    async def register_user(telegram_id, username=None, first_name=None, last_name=None):
        """Register a new user"""
        # Check if user already exists
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            return user, False  # User already exists
        
        # Create new user
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        session.add(user)
        session.commit()
        return user, True  # New user created
    
    @staticmethod
    async def get_user(telegram_id):
        """Get user by Telegram ID"""
        return session.query(User).filter(User.telegram_id == telegram_id).first()
    
    @staticmethod
    async def update_last_active(telegram_id):
        """Update user's last active timestamp"""
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.last_active = datetime.utcnow()
            session.commit()
```

### Registration Handler
```python
async def register_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user registration"""
    telegram_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    last_name = update.effective_user.last_name
    
    user, is_new = await UserService.register_user(
        telegram_id, username, first_name, last_name
    )
    
    if is_new:
        await update.message.reply_text(
            f"Welcome {first_name}! You've been successfully registered.\n"
            f"Use /help to see available commands."
        )
    else:
        await update.message.reply_text(
            f"Welcome back {first_name}! You're already registered.\n"
            f"Use /profile to view your account details."
        )
```

## Subscription Management

### Subscription Model Structure
```python
class SubscriptionPlan(Base):
    __tablename__ = 'subscription_plans'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    price_monthly = Column(Float, nullable=False)
    price_yearly = Column(Float, nullable=False)
    duration_days = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)

class Subscription(Base):
    __tablename__ = 'user_subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    plan_id = Column(Integer, ForeignKey('subscription_plans.id'), nullable=False)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    payment_id = Column(String)  # Telegram payment ID
    payment_status = Column(String)  # pending, completed, failed, refunded
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan")
```

### Subscription Service
```python
class SubscriptionService:
    @staticmethod
    async def get_active_subscription(telegram_id):
        """Get user's active subscription"""
        user = UserService.get_user(telegram_id)
        if not user:
            return None
        
        return session.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.is_active == True,
            Subscription.end_date > datetime.utcnow()
        ).first()
    
    @staticmethod
    async def get_subscription_plans():
        """Get all active subscription plans"""
        return session.query(SubscriptionPlan).filter(
            SubscriptionPlan.is_active == True
        ).all()
    
    @staticmethod
    async def create_subscription(telegram_id, plan_id, payment_id):
        """Create a new subscription"""
        user = UserService.get_user(telegram_id)
        if not user:
            raise ValueError("User not found")
        
        plan = session.query(SubscriptionPlan).get(plan_id)
        if not plan:
            raise ValueError("Plan not found")
        
        # Calculate end date based on plan duration
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=plan.duration_days)
        
        # Create subscription
        subscription = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            start_date=start_date,
            end_date=end_date,
            payment_id=payment_id,
            payment_status="completed"
        )
        
        session.add(subscription)
        session.commit()
        return subscription
    
    @staticmethod
    async def cancel_subscription(subscription_id):
        """Cancel a subscription"""
        subscription = session.query(Subscription).get(subscription_id)
        if subscription:
            subscription.is_active = False
            session.commit()
            return True
        return False
```

### Subscription Handler
```python
async def subscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription command"""
    telegram_id = update.effective_user.id
    
    # Check if user already has an active subscription
    active_subscription = await SubscriptionService.get_active_subscription(telegram_id)
    if active_subscription:
        plan = active_subscription.plan
        await update.message.reply_text(
            f"You already have an active subscription:\n"
            f"Plan: {plan.name}\n"
            f"Expires: {active_subscription.end_date.strftime('%Y-%m-%d')}\n"
            f"Use /subscription to view details."
        )
        return
    
    # Get available subscription plans
    plans = await SubscriptionService.get_subscription_plans()
    if not plans:
        await update.message.reply_text("No subscription plans available at the moment.")
        return
    
    # Create inline keyboard with plan options
    keyboard = []
    for plan in plans:
        # Telegram Payments options
        button_text = f"{plan.name} - {'${:.2f}'.format(plan.price_monthly)}/month"
        callback_data = f"subscribe_{plan.id}_monthly"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        if plan.price_yearly > 0:  # If yearly plan exists
            button_text = f"{plan.name} - {'${:.2f}'.format(plan.price_yearly)}/year"
            callback_data = f"subscribe_{plan.id}_yearly"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        # Chapa payment options (for Ethiopian users)
        button_text = f"💳 {plan.name} via Chapa (ETB)"
        callback_data = f"chapa_subscribe_{plan.id}_monthly"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        if plan.price_yearly > 0:  # If yearly plan exists
            button_text = f"💳 {plan.name} via Chapa Yearly (ETB)"
            callback_data = f"chapa_subscribe_{plan.id}_yearly"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Add a note about Chapa being for Ethiopian users
    keyboard.append([InlineKeyboardButton("ℹ️ Chapa for Ethiopian users", callback_data="chapa_info")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Choose a subscription plan:\n"
        "💳 Chapa is recommended for Ethiopian users (supports mobile money and bank transfers)",
        reply_markup=reply_markup
    )

async def subscription_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription plan selection"""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data
    data_parts = query.data.split("_")
    
    # Handle Chapa payments
    if data_parts[0] == "chapa":
        # Handle Chapa payment
        plan_id = int(data_parts[2])
        billing_cycle = data_parts[3]  # monthly or yearly
        
        # Get plan details
        plan = session.query(SubscriptionPlan).get(plan_id)
        if not plan:
            await query.edit_message_text("Plan not found.")
            return
        
        # Create Chapa payment
        chapa_service = ChapaPaymentService()
        checkout_url = await chapa_service.create_subscription_payment(
            query.from_user.id, plan_id, billing_cycle
        )
        
        # Send message with payment link
        await query.edit_message_text(
            f"Please complete your payment using the link below:\n{checkout_url}\n\n"
            f"After payment, your subscription will be activated automatically."
        )
        
        return
    
    # Handle Telegram Payments (existing functionality)
    if len(data_parts) != 4 or data_parts[0] != "subscribe":
        await query.edit_message_text("Invalid selection.")
        return
    
    plan_id = int(data_parts[1])
    billing_cycle = data_parts[3]  # monthly or yearly
    
    # Get plan details
    plan = session.query(SubscriptionPlan).get(plan_id)
    if not plan:
        await query.edit_message_text("Plan not found.")
        return
    
    # Determine price based on billing cycle
    price = plan.price_monthly if billing_cycle == "monthly" else plan.price_yearly
    
    # Create invoice for Telegram Payments
    title = f"{plan.name} Subscription"
    description = f"{plan.description}\nBilling cycle: {billing_cycle}"
    payload = f"subscription_{plan.id}_{billing_cycle}_{query.from_user.id}"
    currency = "USD"  # Or configurable currency
    prices = [LabeledPrice(plan.name, int(price * 100))]  # Convert to cents
    
    # Send invoice
    await context.bot.send_invoice(
        chat_id=query.from_user.id,
        title=title,
        description=description,
        payload=payload,
        provider_token=PAYMENT_PROVIDER_TOKEN,  # From config
        currency=currency,
        prices=prices,
        start_parameter="subscription-payment"
    )
```

### Payment Handler
```python
async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pre-checkout queries"""
    query = update.pre_checkout_query
    # Check if payment is valid (e.g., check payload)
    # For now, we'll just approve all payments
    await query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful payments"""
    # Extract information from payment
    telegram_id = update.message.from_user.id
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    
    # Parse payload to get plan and billing info
    payload_parts = payload.split("_")
    if len(payload_parts) != 4 or payload_parts[0] != "subscription":
        await update.message.reply_text("Payment error: Invalid payload.")
        return
    
    plan_id = int(payload_parts[1])
    billing_cycle = payload_parts[2]
    payment_id = payment.provider_payment_charge_id
    
    try:
        # Create subscription
        subscription = await SubscriptionService.create_subscription(
            telegram_id, plan_id, payment_id
        )
        
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
    except Exception as e:
        # Log error and notify user
        logger.error(f"Subscription creation failed: {str(e)}")
        await update.message.reply_text(
            "There was an error processing your subscription. "
            "Please contact support."
        )
```

## Profile Management

### Profile Handler
```python
async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle profile command"""
    telegram_id = update.effective_user.id
    user = await UserService.get_user(telegram_id)
    
    if not user:
        await update.message.reply_text("User not found. Please register first with /register")
        return
    
    # Get user's active subscription
    active_subscription = await SubscriptionService.get_active_subscription(telegram_id)
    
    # Format profile information
    profile_text = f"👤 Profile Information\n"
    profile_text += f"Name: {user.first_name} {user.last_name or ''}\n"
    profile_text += f"Username: @{user.username}\n" if user.username else ""
    profile_text += f"Member since: {user.registration_date.strftime('%Y-%m-%d')}\n"
    profile_text += f"Last active: {user.last_active.strftime('%Y-%m-%d %H:%M')}\n"
    
    if active_subscription:
        plan = active_subscription.plan
        profile_text += f"\n💳 Subscription\n"
        profile_text += f"Plan: {plan.name}\n"
        profile_text += f"Status: Active\n"
        profile_text += f"Expires: {active_subscription.end_date.strftime('%Y-%m-%d')}\n"
    else:
        profile_text += f"\n💳 Subscription\n"
        profile_text += f"Status: No active subscription\n"
        profile_text += f"Use /subscribe to get access to premium content\n"
    
    await update.message.reply_text(profile_text)
```

## Security Considerations

1. All user data is stored securely in the database
2. Telegram IDs are used as the primary identifier for users
3. Payment information is handled by Telegram Payments (not stored in our database)
4. User sessions are managed by Telegram (no need for separate session management)
5. Admin commands are protected by checking the is_admin flag

## Error Handling

1. User already registered - Inform user they're already registered
2. User not found - Prompt to register first
3. Invalid subscription plan - Show error message
4. Payment processing errors - Log and notify user to contact support
5. Database errors - Log and show user-friendly error messages

## Future Enhancements

1. Password-based authentication for web integration
2. OAuth integration with social providers
3. Multi-factor authentication
4. Subscription trial periods
5. Subscription upgrade/downgrade functionality
6. Enhanced Chapa integration with support for recurring payments