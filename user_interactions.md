# User Interaction Features Implementation

## Overview
This document outlines the implementation details for user interaction features including notifications, ratings/reviews, and referral rewards in the Telegram bot.

## Notification System

### Notification Model
```python
class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    notification_type = Column(String, nullable=False)  # 'new_content', 'subscription_reminder', etc.
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
```

### Notification Service
```python
class NotificationService:
    @staticmethod
    async def create_notification(user_id, title, message, notification_type):
        """Create a new notification for a user"""
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type
        )
        
        session.add(notification)
        session.commit()
        return notification
    
    @staticmethod
    async def get_user_notifications(telegram_id, limit=10):
        """Get user's notifications"""
        user = UserService.get_user(telegram_id)
        if not user:
            return []
        
        return session.query(Notification).filter(
            Notification.user_id == user.id
        ).order_by(Notification.created_at.desc()).limit(limit).all()
    
    @staticmethod
    async def mark_as_read(notification_id):
        """Mark notification as read"""
        notification = session.query(Notification).get(notification_id)
        if notification:
            notification.is_read = True
            session.commit()
            return True
        return False
    
    @staticmethod
    async def send_telegram_notification(bot, telegram_id, title, message):
        """Send notification via Telegram"""
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=f"🔔 {title}\n\n{message}"
            )
            return True
        except Exception as e:
            logger.error(f"Error sending Telegram notification to {telegram_id}: {str(e)}")
            return False
```

### Notification Handler
```python
async def notifications_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle notifications command"""
    telegram_id = update.effective_user.id
    
    # Get user's notifications
    notifications = await NotificationService.get_user_notifications(telegram_id, limit=10)
    
    if not notifications:
        await update.message.reply_text("You have no notifications.")
        return
    
    # Format notifications
    notifications_text = "🔔 Your Notifications:\n\n"
    
    for notification in notifications:
        status = "✅" if notification.is_read else "🆕"
        timestamp = notification.created_at.strftime('%Y-%m-%d %H:%M')
        notifications_text += f"{status} {notification.title}\n"
        notifications_text += f"  {timestamp}\n"
        notifications_text += f"  {notification.message}\n\n"
        
        # Mark as read if it's unread
        if not notification.is_read:
            await NotificationService.mark_as_read(notification.id)
    
    await update.message.reply_text(notifications_text)

async def send_new_content_notification(content_id):
    """Send notification to all users about new content"""
    # Get content details
    content = session.query(Content).get(content_id)
    if not content:
        return
    
    # Get all users
    users = session.query(User).all()
    
    title = "New Content Available!"
    message = f"Check out the new {content.content_type}: {content.title}"
    
    for user in users:
        # Create notification record
        await NotificationService.create_notification(
            user.id, title, message, "new_content"
        )
        
        # Send Telegram notification (in a real implementation, 
        # this would be done in batches to avoid rate limits)
        # await NotificationService.send_telegram_notification(
        #     context.bot, user.telegram_id, title, message
        #     )

# In content upload handler, after successful upload:
# await send_new_content_notification(content.id)
```

## Rating and Review System

### User Interaction Model
```python
class UserInteraction(Base):
    __tablename__ = 'user_content_interactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content_id = Column(Integer, ForeignKey('content.id'), nullable=False)
    interaction_type = Column(String, nullable=False)  # 'view', 'download', 'rate', 'review'
    interaction_date = Column(DateTime, default=datetime.utcnow)
    rating = Column(Integer)  # 1-5 stars
    review = Column(String)  # User review text
    
    # Relationships
    user = relationship("User", back_populates="interactions")
    content = relationship("Content", back_populates="interactions")
    
    __table_args__ = (UniqueConstraint('user_id', 'content_id', 'interaction_type'),)
```

### Rating Handler
```python
async def rate_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle content rating"""
    query = update.callback_query
    await query.answer()
    
    # Parse content ID from callback data
    data_parts = query.data.split("_")
    if len(data_parts) != 2 or data_parts[0] != "rate":
        await query.edit_message_text("Invalid rating request.")
        return
    
    content_id = int(data_parts[1])
    
    # Get content details
    content = session.query(Content).get(content_id)
    if not content:
        await query.edit_message_text("Content not found.")
        return
    
    # Create rating keyboard
    keyboard = []
    for i in range(1, 6):
        button_text = "⭐" * i
        callback_data = f"rating_{content_id}_{i}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"content_{content_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    content_type_text = "Video" if content.content_type == "video" else "Book"
    await query.edit_message_text(
        f"Rate this {content_type_text.lower()}:\n"
        f"⭐ {content.title}\n\n"
        f"Select your rating:",
        reply_markup=reply_markup
    )

async def rating_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rating selection"""
    query = update.callback_query
    await query.answer()
    
    # Parse rating data
    data_parts = query.data.split("_")
    if len(data_parts) != 3 or data_parts[0] != "rating":
        await query.edit_message_text("Invalid rating selection.")
        return
    
    content_id = int(data_parts[1])
    rating = int(data_parts[2])
    
    # Get content details
    content = session.query(Content).get(content_id)
    if not content:
        await query.edit_message_text("Content not found.")
        return
    
    # Get user
    telegram_id = query.from_user.id
    user = UserService.get_user(telegram_id)
    if not user:
        await query.edit_message_text("User not found.")
        return
    
    # Check if user has interacted with this content
    interaction = session.query(UserInteraction).filter(
        UserInteraction.user_id == user.id,
        UserInteraction.content_id == content_id,
        UserInteraction.interaction_type == "rate"
    ).first()
    
    if interaction:
        # Update existing rating
        interaction.rating = rating
        interaction.interaction_date = datetime.utcnow()
    else:
        # Create new rating
        interaction = UserInteraction(
            user_id=user.id,
            content_id=content_id,
            interaction_type="rate",
            rating=rating
        )
        session.add(interaction)
    
    session.commit()
    
    # Calculate new average rating
    ratings = session.query(UserInteraction).filter(
        UserInteraction.content_id == content_id,
        UserInteraction.interaction_type == "rate"
    ).all()
    
    if ratings:
        avg_rating = sum(r.rating for r in ratings) / len(ratings)
        content.rating = round(avg_rating, 1)
        session.commit()
    
    await query.edit_message_text(
        f"Thank you for rating!\n"
        f"You gave {content.title} {rating} stars.\n"
        f"Average rating: {content.rating if hasattr(content, 'rating') else 'N/A'} stars."
    )

async def review_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle content review"""
    query = update.callback_query
    await query.answer()
    
    # Parse content ID from callback data
    data_parts = query.data.split("_")
    if len(data_parts) != 3 or data_parts[0] != "review":
        await query.edit_message_text("Invalid review request.")
        return
    
    content_id = int(data_parts[2])
    
    # Get content details
    content = session.query(Content).get(content_id)
    if not content:
        await query.edit_message_text("Content not found.")
        return
    
    await query.edit_message_text(
        f"Please write your review for:\n"
        f"⭐ {content.title}\n\n"
        f"Send your review as a message."
    )
    
    # Set conversation state
    context.user_data['review_state'] = {
        'content_id': content_id,
        'waiting_for_review': True
    }

async def review_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle review message input"""
    # Check if we're in review state
    review_state = context.user_data.get('review_state', {})
    if not review_state.get('waiting_for_review'):
        return
    
    content_id = review_state['content_id']
    review_text = update.message.text
    
    # Get content details
    content = session.query(Content).get(content_id)
    if not content:
        await update.message.reply_text("Content not found.")
        return
    
    # Get user
    telegram_id = update.effective_user.id
    user = UserService.get_user(telegram_id)
    if not user:
        await update.message.reply_text("User not found.")
        return
    
    # Check if user has already reviewed this content
    interaction = session.query(UserInteraction).filter(
        UserInteraction.user_id == user.id,
        UserInteraction.content_id == content_id,
        UserInteraction.interaction_type == "review"
    ).first()
    
    if interaction:
        # Update existing review
        interaction.review = review_text
        interaction.interaction_date = datetime.utcnow()
    else:
        # Create new review
        interaction = UserInteraction(
            user_id=user.id,
            content_id=content_id,
            interaction_type="review",
            review=review_text
        )
        session.add(interaction)
    
    session.commit()
    
    await update.message.reply_text(
        f"Thank you for your review of {content.title}!\n"
        f"Your review: {review_text}"
    )
    
    # Clear review state
    context.user_data.pop('review_state', None)
```

## Referral System

### Referral Model
```python
class Referral(Base):
    __tablename__ = 'referrals'
    
    id = Column(Integer, primary_key=True)
    referrer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    referred_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    referral_date = Column(DateTime, default=datetime.utcnow)
    reward_claimed = Column(Boolean, default=False)
    
    # Relationships
    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals")
    referred = relationship("User", foreign_keys=[referred_id], back_populates="referred_by")
    
    __table_args__ = (UniqueConstraint('referred_id'),)
```

### Referral Service
```python
class ReferralService:
    @staticmethod
    async def create_referral(referrer_id, referred_id):
        """Create a new referral relationship"""
        # Check if referred user already has a referral
        existing_referral = session.query(Referral).filter(
            Referral.referred_id == referred_id
        ).first()
        
        if existing_referral:
            return existing_referral, False  # Already exists
        
        # Create new referral
        referral = Referral(
            referrer_id=referrer_id,
            referred_id=referred_id
        )
        
        session.add(referral)
        session.commit()
        return referral, True  # New referral created
    
    @staticmethod
    async def get_user_referrals(telegram_id):
        """Get user's referral information"""
        user = UserService.get_user(telegram_id)
        if not user:
            return None
        
        # Get referrals made by user
        referrals = session.query(Referral).filter(
            Referral.referrer_id == user.id
        ).all()
        
        # Get user's referrer
        user_referral = session.query(Referral).filter(
            Referral.referred_id == user.id
        ).first()
        
        return {
            'referrals_made': referrals,
            'referred_by': user_referral.referrer if user_referral else None
        }
    
    @staticmethod
    async def claim_referral_reward(telegram_id):
        """Claim referral reward for user"""
        user = UserService.get_user(telegram_id)
        if not user:
            return False, "User not found"
        
        # Check if user was referred
        referral = session.query(Referral).filter(
            Referral.referred_id == user.id
        ).first()
        
        if not referral:
            return False, "You were not referred by another user"
        
        if referral.reward_claimed:
            return False, "Reward already claimed"
        
        # Mark reward as claimed
        referral.reward_claimed = True
        session.commit()
        
        # Here you would implement the actual reward logic
        # For example, extend subscription or add credits
        
        return True, "Reward claimed successfully"
```

### Referral Handler
```python
async def referral_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle referral command"""
    telegram_id = update.effective_user.id
    
    # Get user's referral information
    referral_info = await ReferralService.get_user_referrals(telegram_id)
    
    if not referral_info:
        await update.message.reply_text("User not found.")
        return
    
    # Format referral information
    referral_text = "🎁 Referral Program\n\n"
    
    # Show referrer information
    if referral_info['referred_by']:
        referrer = referral_info['referred_by']
        referral_text += f"👨‍💼 Referred by: {referrer.first_name} {referrer.last_name or ''}\n"
        referral_text += f"{'✅ Reward claimed' if referral_info['referred_by'].reward_claimed else '❌ Reward not claimed'}\n\n"
    else:
        referral_text += "You were not referred by another user.\n\n"
    
    # Show referrals made
    referrals_made = referral_info['referrals_made']
    if referrals_made:
        referral_text += f"👥 You have referred {len(referrals_made)} user(s):\n"
        for referral in referrals_made:
            referred_user = UserService.get_user(referral.referred_id)
            if referred_user:
                referral_text += f"  - {referred_user.first_name} {referred_user.last_name or ''} "
                referral_text += f"({'✅ Reward claimed' if referral.reward_claimed else '⏳ Pending reward'})\n"
    else:
        referral_text += "You haven't referred any users yet.\n\n"
    
    # Show referral link
    referral_text += f"\n🔗 Your referral link:\n"
    referral_text += f"https://t.me/your_bot_username?start=ref_{telegram_id}\n\n"
    referral_text += "Share this link with friends to earn rewards!"
    
    # Create keyboard for claiming reward if applicable
    keyboard = []
    
    # Check if user can claim reward
    user_referral = session.query(Referral).filter(
        Referral.referred_id == telegram_id
    ).first()
    
    if user_referral and not user_referral.reward_claimed:
        keyboard.append([InlineKeyboardButton("🎁 Claim Referral Reward", callback_data="claim_referral_reward")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(referral_text, reply_markup=reply_markup)

async def claim_referral_reward_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle referral reward claim"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    
    # Claim referral reward
    success, message = await ReferralService.claim_referral_reward(telegram_id)
    
    if success:
        # In a real implementation, you would actually grant the reward here
        # For example, extend subscription by 7 days or add credits
        
        await query.edit_message_text(
            "🎉 Reward claimed successfully!\n"
            "Your subscription has been extended by 7 days.\n"
            "Thank you for using our referral program!"
        )
    else:
        await query.edit_message_text(f"❌ {message}")

async def process_referral_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process referral from start parameter"""
    # Check if start parameter contains referral info
    if context.args and len(context.args) > 0:
        start_param = context.args[0]
        if start_param.startswith("ref_"):
            try:
                referrer_id = int(start_param[4:])  # Remove "ref_" prefix
                
                # Get referred user
                referred_id = update.effective_user.id
                
                # Create referral if it doesn't exist
                referral, is_new = await ReferralService.create_referral(referrer_id, referred_id)
                
                if is_new:
                    # Send notification to referrer
                    referrer = UserService.get_user(referrer_id)
                    if referrer:
                        await NotificationService.create_notification(
                            referrer.id,
                            "New Referral!",
                            f"{update.effective_user.first_name} joined using your referral link!",
                            "referral"
                        )
                        
                        # In a real implementation, you might want to send a Telegram notification
                        # await NotificationService.send_telegram_notification(
                        #     context.bot, referrer.telegram_id, "New Referral!", 
                        #     f"{update.effective_user.first_name} joined using your referral link!"
                        # )
                        
            except ValueError:
                pass  # Invalid referrer ID
```

## User Interaction Integration

### Content Details Integration
```python
# In content_details_handler, add rating/review buttons:
async def content_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced content details handler with rating/review"""
    # ... existing code ...
    
    # Add rating/review buttons if user has interacted with content
    keyboard = []
    
    if content.is_premium and not has_access:
        # Premium content access buttons
        keyboard.append([InlineKeyboardButton("💳 Subscribe", callback_data="subscribe_start")])
    else:
        # Content access buttons
        keyboard.append([InlineKeyboardButton("📥 Access Content", callback_data=f"access_{content.id}")])
        
        # Check if user has already rated/reviewed
        telegram_id = query.from_user.id
        user = UserService.get_user(telegram_id)
        if user:
            # Check for existing rating
            existing_rating = session.query(UserInteraction).filter(
                UserInteraction.user_id == user.id,
                UserInteraction.content_id == content.id,
                UserInteraction.interaction_type == "rate"
            ).first()
            
            # Check for existing review
            existing_review = session.query(UserInteraction).filter(
                UserInteraction.user_id == user.id,
                UserInteraction.content_id == content.id,
                UserInteraction.interaction_type == "review"
            ).first()
            
            rating_text = "⭐ Update Rating" if existing_rating else "⭐ Rate Content"
            review_text = "📝 Update Review" if existing_review else "📝 Write Review"
            
            keyboard.append([InlineKeyboardButton(rating_text, callback_data=f"rate_{content.id}")])
            keyboard.append([InlineKeyboardButton(review_text, callback_data=f"review_content_{content.id}")])
    
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"category_{content.category_id}_{content.content_type}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Add rating information to content details
    if hasattr(content, 'rating') and content.rating:
        details_text += f"⭐ Rating: {content.rating}/5\n"
    
    await query.edit_message_text(details_text, reply_markup=reply_markup)
```

## Error Handling and User Feedback

### Error Handling
1. Invalid notification IDs - Log and show user-friendly message
2. Database errors in notification creation - Log and notify admin
3. Telegram API errors in sending notifications - Retry with exponential backoff
4. Invalid rating values - Validate and show error message
5. Duplicate reviews - Update existing review instead of creating new
6. Referral already exists - Return existing referral information
7. Invalid referral IDs in start parameter - Ignore and proceed normally

## Future Enhancements

1. Notification preferences for users (email, SMS, Telegram)
2. Scheduled notifications for content releases
3. Advanced review features (pros/cons, helpful votes)
4. Referral tier system (multi-level referrals)
5. Social sharing features for content
6. User badges and achievements system
7. Content recommendation based on ratings
8. Automated notifications for subscription renewals
9. In-app messaging between users
10. Community features (discussion forums for content)