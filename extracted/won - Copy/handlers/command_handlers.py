# Command handlers for the Telegram bot
import logging
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from database import SessionLocal
from models.user import User
from models.subscription_plan import SubscriptionPlan
from services.subscription_service import SubscriptionService
from services.payment_service import ChapaPaymentService

logger = logging.getLogger(__name__)

async def start_command(client: Client, message: Message):
    """Handle /start command"""
    user = message.from_user
    session = SessionLocal()
    
    try:
        # Check if user exists, create if not
        db_user = session.query(User).filter(User.telegram_id == user.id).first()
        if not db_user:
            db_user = User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            session.add(db_user)
            session.commit()
            logger.info(f"New user registered: {user.id}")
        
        # Check for active subscription
        active_sub = await SubscriptionService.get_active_subscription(user.id, session)
        
        if active_sub:
            await message.reply_text(
                f"Welcome back, {user.first_name}! 🎉\n\n"
                f"Your {active_sub.plan.name} subscription is active until {active_sub.end_date.strftime('%Y-%m-%d')}.\n\n"
                "You have access to all premium content!"
            )
        else:
            keyboard = [
                [InlineKeyboardButton("📋 View Plans", callback_data="view_plans")],
                [InlineKeyboardButton("ℹ️ About", callback_data="about")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await message.reply_text(
                f"Welcome to the Content Bot, {user.first_name}! 🤖\n\n"
                "Get access to premium educational content including:\n"
                "📚 Exclusive books\n"
                "🎥 Video tutorials\n"
                "📖 Study materials\n\n"
                "Choose an option below:",
                reply_markup=reply_markup
            )
    
    finally:
        session.close()

async def subscribe_command(client: Client, message: Message):
    """Handle /subscribe command"""
    session = SessionLocal()
    
    try:
        plans = await SubscriptionService.get_subscription_plans(session)
        
        if not plans:
            await message.reply_text("No subscription plans available at the moment.")
            return
        
        keyboard = []
        for plan in plans:
            keyboard.append([
                InlineKeyboardButton(
                    f"{plan.name} - {plan.price_monthly} ETB/month",
                    callback_data=f"select_plan_{plan.id}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            "📋 **Available Subscription Plans:**\n\n"
            "Choose a plan that works for you:",
            reply_markup=reply_markup
        )
    
    finally:
        session.close()

async def status_command(client: Client, message: Message):
    """Handle /status command"""
    user = message.from_user
    session = SessionLocal()
    
    try:
        active_sub = await SubscriptionService.get_active_subscription(user.id, session)
        
        if active_sub:
            days_left = (active_sub.end_date - active_sub.start_date).days
            await message.reply_text(
                f"📊 **Subscription Status**\n\n"
                f"Plan: {active_sub.plan.name}\n"
                f"Status: ✅ Active\n"
                f"Expires: {active_sub.end_date.strftime('%Y-%m-%d')}\n"
                f"Days remaining: {days_left}\n"
                f"Payment Status: {active_sub.payment_status}"
            )
        else:
            keyboard = [[InlineKeyboardButton("📋 View Plans", callback_data="view_plans")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await message.reply_text(
                "❌ **No Active Subscription**\n\n"
                "You don't have an active subscription. Subscribe now to access premium content!",
                reply_markup=reply_markup
            )
    
    finally:
        session.close()

async def help_command(client: Client, message: Message):
    """Handle /help command"""
    help_text = """
🤖 **Bot Commands:**

/start - Start the bot and see your status
/subscribe - View and select subscription plans
/status - Check your subscription status
/help - Show this help message

📋 **Available Plans:**
• Monthly Premium - Full access for 30 days
• Yearly Premium - Full access for 365 days (best value!)

💳 **Payment Methods:**
• Chapa - Ethiopian mobile money and bank transfers

❓ **Need Help?**
Contact support for any questions or issues.
    """
    
    await message.reply_text(help_text)

# Callback query handlers
async def button_callback(client: Client, callback_query: CallbackQuery):
    """Handle button callbacks"""
    await callback_query.answer()
    
    session = SessionLocal()
    
    try:
        if callback_query.data == "view_plans":
            plans = await SubscriptionService.get_subscription_plans(session)
            
            keyboard = []
            for plan in plans:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{plan.name} - {plan.price_monthly} ETB/month",
                        callback_data=f"select_plan_{plan.id}"
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await callback_query.edit_message_text(
                "📋 **Available Subscription Plans:**\n\n"
                "Choose a plan that works for you:",
                reply_markup=reply_markup
            )
        
        elif callback_query.data.startswith("select_plan_"):
            plan_id = int(callback_query.data.split("_")[2])
            plan = session.query(SubscriptionPlan).get(plan_id)
            
            if plan:
                keyboard = [
                    [InlineKeyboardButton("💳 Pay with Chapa", callback_data=f"pay_chapa_{plan_id}")],
                    [InlineKeyboardButton("🔙 Back to Plans", callback_data="view_plans")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await callback_query.edit_message_text(
                    f"📋 **{plan.name}**\n\n"
                    f"{plan.description}\n\n"
                    f"💰 Price: {plan.price_monthly} ETB/month\n"
                    f"⏰ Duration: {plan.duration_days} days\n\n"
                    "Choose your payment method:",
                    reply_markup=reply_markup
                )
        
        elif callback_query.data.startswith("pay_chapa_"):
            plan_id = int(callback_query.data.split("_")[2])
            user_id = callback_query.from_user.id
            
            try:
                chapa_service = ChapaPaymentService()
                checkout_url = await chapa_service.create_subscription_payment(
                    user_id, plan_id, "monthly", session
                )
                
                keyboard = [[InlineKeyboardButton("💳 Complete Payment", url=checkout_url)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await callback_query.edit_message_text(
                    "💳 **Payment Ready**\n\n"
                    "Click the button below to complete your payment with Chapa.\n\n"
                    "After successful payment, your subscription will be activated automatically!",
                    reply_markup=reply_markup
                )
                
            except Exception as e:
                logger.error(f"Error creating Chapa payment: {str(e)}")
                await callback_query.edit_message_text(
                    "❌ **Payment Error**\n\n"
                    "Sorry, there was an error processing your payment. Please try again later."
                )
        
        elif callback_query.data == "about":
            await callback_query.edit_message_text(
                "📚 **About Content Bot**\n\n"
                "This bot provides access to premium educational content including:\n\n"
                "📖 **Books** - Curated collection of educational books\n"
                "🎥 **Videos** - High-quality tutorial videos\n"
                "📝 **Materials** - Study guides and resources\n\n"
                "Subscribe to unlock all content!"
            )
    
    finally:
        session.close()
