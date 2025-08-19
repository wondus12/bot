# Telegram bot handlers for content delivery and device management
import logging
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from database import SessionLocal
from models.user import User
from models.device import Device
from models.content import Content
from services.device_service import DeviceService
from services.content_service import ContentService
from services.subscription_service import SubscriptionService
import json

logger = logging.getLogger(__name__)

async def register_device_command(client: Client, message: Message):
    """Handle /register_device command"""
    user = message.from_user
    session = SessionLocal()
    
    try:
        # Check if user has active subscription
        subscription = await SubscriptionService.get_active_subscription(user.id, session)
        if not subscription:
            await message.reply_text(
                "❌ **Device Registration Failed**\n\n"
                "You need an active subscription to register devices.\n"
                "Use /subscribe to get started!"
            )
            return
        
        # Show device registration instructions
        keyboard = [
            [InlineKeyboardButton("📱 Register Mobile Device", callback_data="register_mobile")],
            [InlineKeyboardButton("💻 Register Laptop", callback_data="register_laptop")],
            [InlineKeyboardButton("📋 View My Devices", callback_data="view_devices")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            "🔐 **Device Registration**\n\n"
            "To access protected content, you need to register your devices.\n\n"
            "**Device Limits:**\n"
            "• 1 Mobile device (Android/iOS)\n"
            "• 1 Laptop (Windows/macOS)\n\n"
            "Choose an option below:",
            reply_markup=reply_markup
        )
    
    finally:
        session.close()

async def content_library_command(client: Client, message: Message):
    """Handle /library command - show available content"""
    user = message.from_user
    session = SessionLocal()
    
    try:
        # Check subscription
        subscription = await SubscriptionService.get_active_subscription(user.id, session)
        if not subscription:
            await message.reply_text(
                "❌ **Access Denied**\n\n"
                "You need an active subscription to access the content library.\n"
                "Use /subscribe to get started!"
            )
            return
        
        # Get available content
        content_list = await ContentService.list_user_content(user.id, session)
        
        if not content_list:
            await message.reply_text(
                "📚 **Content Library**\n\n"
                "No content available at the moment.\n"
                "Check back later for new releases!"
            )
            return
        
        # Create content buttons
        keyboard = []
        for content in content_list[:10]:  # Limit to 10 items per page
            icon = "🎥" if content.content_type == "video" else "📄" if content.content_type == "pdf" else "🎵"
            keyboard.append([
                InlineKeyboardButton(
                    f"{icon} {content.title}",
                    callback_data=f"content_{content.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔐 Manage Devices", callback_data="view_devices")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            f"📚 **Content Library**\n\n"
            f"Available content: {len(content_list)} items\n\n"
            "Select content to download:",
            reply_markup=reply_markup
        )
    
    finally:
        session.close()

async def device_callback_handler(client: Client, callback_query: CallbackQuery):
    """Handle device-related callback queries"""
    await callback_query.answer()
    
    session = SessionLocal()
    
    try:
        if callback_query.data == "register_mobile":
            await callback_query.edit_message_text(
                "📱 **Mobile Device Registration**\n\n"
                "To register your mobile device, you need to use our mobile app.\n\n"
                "**Steps:**\n"
                "1. Download the app from App Store/Play Store\n"
                "2. Login with your Telegram account\n"
                "3. The app will automatically register your device\n\n"
                "**Device Info Collected:**\n"
                "• Device model and OS version\n"
                "• Unique hardware identifier\n"
                "• Screen resolution and timezone\n\n"
                "This ensures content is locked to your specific device.",
                parse_mode='Markdown'
            )
        
        elif callback_query.data == "register_laptop":
            await callback_query.edit_message_text(
                "💻 **Laptop Registration**\n\n"
                "To register your laptop, visit our web portal:\n\n"
                "**Steps:**\n"
                "1. Go to: https://secure.yourbot.com/register\n"
                "2. Login with your Telegram account\n"
                "3. Allow browser to collect device fingerprint\n"
                "4. Complete registration\n\n"
                "**Device Info Collected:**\n"
                "• Hardware specifications\n"
                "• Browser fingerprint\n"
                "• TPM/Secure enclave data (if available)\n\n"
                "Content will be locked to this specific laptop.",
                parse_mode='Markdown'
            )
        
        elif callback_query.data == "view_devices":
            user_id = callback_query.from_user.id
            devices = await DeviceService.get_user_devices(user_id, session)
            
            if not devices:
                await callback_query.edit_message_text(
                    "🔐 **My Devices**\n\n"
                    "No devices registered yet.\n\n"
                    "Register your devices to access protected content.",
                    parse_mode='Markdown'
                )
                return
            
            device_text = "🔐 **My Devices**\n\n"
            keyboard = []
            
            for device in devices:
                status = "✅ Active" if device.is_active else "❌ Inactive"
                device_text += f"**{device.device_name}**\n"
                device_text += f"Type: {device.device_type.title()}\n"
                device_text += f"Platform: {device.platform.title()}\n"
                device_text += f"Status: {status}\n"
                device_text += f"Last seen: {device.last_seen.strftime('%Y-%m-%d %H:%M')}\n\n"
                
                if device.is_active:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"🚫 Revoke {device.device_name}",
                            callback_data=f"revoke_{device.device_id}"
                        )
                    ])
            
            keyboard.append([InlineKeyboardButton("🔙 Back to Library", callback_data="back_to_library")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await callback_query.edit_message_text(device_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif callback_query.data.startswith("revoke_"):
            device_id = callback_query.data.split("_", 1)[1]
            user_id = callback_query.from_user.id
            
            success = await DeviceService.revoke_device(user_id, device_id, session)
            
            if success:
                await callback_query.edit_message_text(
                    "✅ **Device Revoked**\n\n"
                    "The device has been successfully revoked.\n"
                    "It will no longer be able to access protected content.\n\n"
                    "You can register a new device anytime.",
                    parse_mode='Markdown'
                )
            else:
                await callback_query.edit_message_text(
                    "❌ **Revocation Failed**\n\n"
                    "Could not revoke the device. Please try again.",
                    parse_mode='Markdown'
                )
        
        elif callback_query.data.startswith("content_"):
            content_id = int(callback_query.data.split("_")[1])
            user_id = callback_query.from_user.id
            
            # Get content details
            content = session.query(Content).get(content_id)
            if not content:
                await callback_query.edit_message_text("❌ Content not found.")
                return
            
            # Get user's devices
            devices = await DeviceService.get_user_devices(user_id, session)
            
            if not devices:
                keyboard = [[InlineKeyboardButton("🔐 Register Device", callback_data="register_mobile")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await callback_query.edit_message_text(
                    "🔐 **Device Required**\n\n"
                    "You need to register a device to download protected content.\n\n"
                    "Register your device first:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return
            
            # Show content details and download options
            icon = "🎥" if content.content_type == "video" else "📄" if content.content_type == "pdf" else "🎵"
            size_mb = content.file_size / (1024 * 1024) if content.file_size else 0
            
            content_text = f"{icon} **{content.title}**\n\n"
            content_text += f"**Description:** {content.description}\n"
            content_text += f"**Type:** {content.content_type.title()}\n"
            content_text += f"**Size:** {size_mb:.1f} MB\n\n"
            content_text += "**Download to:**\n"
            
            keyboard = []
            for device in devices:
                device_icon = "📱" if device.device_type == "mobile" else "💻"
                keyboard.append([
                    InlineKeyboardButton(
                        f"{device_icon} {device.device_name}",
                        callback_data=f"download_{content_id}_{device.device_id}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("🔙 Back to Library", callback_data="back_to_library")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await callback_query.edit_message_text(content_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif callback_query.data.startswith("download_"):
            parts = callback_query.data.split("_")
            content_id = int(parts[1])
            device_id = parts[2]
            user_id = callback_query.from_user.id
            
            try:
                # Get content for device
                content_info = await ContentService.get_content_for_device(
                    user_id, content_id, device_id, session
                )
                
                content = content_info['content']
                encrypted_key = content_info['encrypted_key']
                
                # Create download instructions
                download_text = f"🔐 **Download Ready**\n\n"
                download_text += f"**Content:** {content.title}\n"
                download_text += f"**Device:** {device_id[:8]}...\n\n"
                download_text += "**Next Steps:**\n"
                
                if content.content_type == "video":
                    download_text += "1. Open the mobile app or web portal\n"
                    download_text += "2. Use this download code: `" + encrypted_key[:16] + "...`\n"
                    download_text += "3. Video will be encrypted for your device only\n"
                    download_text += "4. Use built-in player for secure playback\n\n"
                    download_text += "⚠️ **Security Notice:**\n"
                    download_text += "• Video is device-locked and encrypted\n"
                    download_text += "• Cannot be played on other devices\n"
                    download_text += "• Screen recording is blocked\n"
                
                elif content.content_type == "pdf":
                    download_text += "1. Open the mobile app or web portal\n"
                    download_text += "2. Use this download code: `" + encrypted_key[:16] + "...`\n"
                    download_text += "3. PDF will be device-locked\n"
                    download_text += "4. Use built-in viewer only\n\n"
                    download_text += "⚠️ **Security Notice:**\n"
                    download_text += "• PDF is device-locked\n"
                    download_text += "• Printing and copying disabled\n"
                    download_text += "• Watermarked with device ID\n"
                
                await callback_query.edit_message_text(download_text, parse_mode='Markdown')
                
            except Exception as e:
                logger.error(f"Download error: {str(e)}")
                await callback_query.edit_message_text(
                    f"❌ **Download Failed**\n\n"
                    f"Error: {str(e)}\n\n"
                    "Please try again or contact support.",
                    parse_mode='Markdown'
                )
        
        elif query.data == "back_to_library":
            # Redirect to library command
            await content_library_command(client, callback_query.message)
    
    finally:
        session.close()

# Security monitoring functions
async def detect_suspicious_activity(user_id, device_id, activity_type, session):
    """Detect and log suspicious activities"""
    # Check for multiple simultaneous downloads
    from datetime import datetime, timedelta
    recent_accesses = session.query(ContentAccess).filter(
        ContentAccess.user_id == user_id,
        ContentAccess.access_date > datetime.utcnow() - timedelta(minutes=5)
    ).count()
    
    if recent_accesses > 3:
        logger.warning(f"Suspicious activity: Multiple downloads for user {user_id}")
        return True
    
    return False

async def log_security_event(event_type, user_id, device_id, details, session):
    """Log security events for monitoring"""
    logger.info(f"Security Event: {event_type} - User: {user_id} - Device: {device_id} - {details}")
    
    # In production, send to security monitoring system
    # Could integrate with services like DataDog, Splunk, etc.
