# Admin Controls for Content Management Implementation

## Overview
This document outlines the implementation details for admin controls that will allow administrators to manage content, users, subscriptions, and other aspects of the Telegram bot platform.

## Admin Authentication

### Admin Check Decorator
```python
def admin_required(func):
    """Decorator to check if user is admin"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_id = update.effective_user.id
        user = UserService.get_user(telegram_id)
        
        if not user or not user.is_admin:
            await update.message.reply_text("You don't have permission to use this command.")
            return
        
        return await func(update, context)
    
    return wrapper
```

## Content Management

### Admin Content Handler
```python
@admin_required
async def admin_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin content management command"""
    keyboard = [
        [InlineKeyboardButton("➕ Upload Content", callback_data="admin_upload_content")],
        [InlineKeyboardButton("✏️ Edit Content", callback_data="admin_edit_content")],
        [InlineKeyboardButton("🗑️ Delete Content", callback_data="admin_delete_content")],
        [InlineKeyboardButton("📂 Manage Categories", callback_data="admin_manage_categories")],
        [InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📚 Content Management\n"
        "Select an action:",
        reply_markup=reply_markup
    )

@admin_required
async def admin_upload_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle content upload process"""
    query = update.callback_query
    await query.answer()
    
    # Ask for content type
    keyboard = [
        [InlineKeyboardButton("📹 Video", callback_data="admin_upload_video")],
        [InlineKeyboardButton("📚 Book", callback_data="admin_upload_book")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_content")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "What type of content are you uploading?",
        reply_markup=reply_markup
    )

@admin_required
async def admin_upload_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle content type selection for upload"""
    query = update.callback_query
    await query.answer()
    
    content_type = "video" if "video" in query.data else "book"
    
    # Store content type in user context
    context.user_data['upload_content_type'] = content_type
    
    await query.edit_message_text(
        f"Please upload the {content_type} file you want to add.\n"
        f"Send the file as a document."
    )
    
    # Set conversation state
    context.user_data['upload_state'] = 'waiting_for_file'

async def admin_file_upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file upload for content"""
    # Check if we're in upload state
    if context.user_data.get('upload_state') != 'waiting_for_file':
        return
    
    content_type = context.user_data.get('upload_content_type')
    
    # Get file from message
    if content_type == "video":
        if not update.message.video:
            await update.message.reply_text("Please upload a video file.")
            return
        file = update.message.video
    else:  # book
        if not update.message.document:
            await update.message.reply_text("Please upload a document file.")
            return
        file = update.message.document
    
    # Save file and get path
    try:
        file_path = FileUtils.save_uploaded_file(file, content_type, "temp")
        
        # Validate file type
        if not FileUtils.is_valid_file_type(file_path, content_type):
            FileUtils.delete_content_file(file_path)
            await update.message.reply_text(
                f"Invalid file type for {content_type}. "
                f"Please upload a valid file."
            )
            return
        
        # Store file path in context
        context.user_data['upload_file_path'] = file_path
        
        # Ask for content details
        await update.message.reply_text(
            "Please provide the content details:\n"
            "1. Title\n"
            "2. Description\n"
            "3. Category ID (use /admin_categories to see categories)\n"
            "4. Is this premium content? (yes/no)\n"
            "5. Author (for books only)\n\n"
            "Format your response as:\n"
            "Title: [title]\n"
            "Description: [description]\n"
            "Category ID: [category_id]\n"
            "Premium: [yes/no]\n"
            "Author: [author_name] (optional for books)"
        )
        
        # Set conversation state
        context.user_data['upload_state'] = 'waiting_for_details'
        
    except Exception as e:
        logger.error(f"Error handling file upload: {str(e)}")
        await update.message.reply_text(
            "Error processing file upload. Please try again."
        )

async def admin_content_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle content details input"""
    # Check if we're in details state
    if context.user_data.get('upload_state') != 'waiting_for_details':
        return
    
    # Parse content details from message
    message_text = update.message.text
    lines = message_text.split('\n')
    
    content_data = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            content_data[key.strip().lower()] = value.strip()
    
    # Validate required fields
    required_fields = ['title', 'description', 'category id', 'premium']
    missing_fields = [field for field in required_fields if field not in content_data]
    
    if missing_fields:
        await update.message.reply_text(
            f"Missing required fields: {', '.join(missing_fields)}\n"
            f"Please provide all required information."
        )
        return
    
    # Validate category exists
    try:
        category_id = int(content_data['category id'])
        category = session.query(Category).get(category_id)
        if not category:
            await update.message.reply_text("Invalid category ID.")
            return
    except ValueError:
        await update.message.reply_text("Category ID must be a number.")
        return
    
    # Validate premium field
    is_premium = content_data['premium'].lower() in ['yes', 'true', '1']
    
    # Get file path from context
    file_path = context.user_data.get('upload_file_path')
    content_type = context.user_data.get('upload_content_type')
    
    # Extract metadata based on content type
    if content_type == "video":
        metadata = FileUtils.extract_video_metadata(file_path)
    else:  # book
        metadata = FileUtils.extract_book_metadata(file_path)
        # Add author if provided
        if 'author' in content_data:
            metadata['author'] = content_data['author']
    
    # Create content record
    try:
        content = Content(
            title=content_data['title'],
            description=content_data['description'],
            category_id=category_id,
            content_type=content_type,
            file_path=file_path,
            is_premium=is_premium,
            **metadata
        )
        
        session.add(content)
        session.commit()
        
        await update.message.reply_text(
            f"✅ Content uploaded successfully!\n"
            f"Title: {content.title}\n"
            f"ID: {content.id}\n"
            f"Type: {content.content_type}\n"
            f"Category: {category.name}"
        )
        
        # Clear upload state
        context.user_data.pop('upload_state', None)
        context.user_data.pop('upload_content_type', None)
        context.user_data.pop('upload_file_path', None)
        
    except Exception as e:
        logger.error(f"Error creating content: {str(e)}")
        await update.message.reply_text(
            "Error creating content. Please try again."
        )
```

## Category Management

### Admin Category Handler
```python
@admin_required
async def admin_categories_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin category management"""
    query = update.callback_query
    await query.answer()
    
    # Get all categories
    categories = session.query(Category).all()
    
    keyboard = []
    
    for category in categories:
        status = "✅" if category.is_active else "❌"
        button_text = f"{status} {category.name} ({category.content_type})"
        callback_data = f"admin_edit_category_{category.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Add action buttons
    keyboard.extend([
        [InlineKeyboardButton("➕ Add New Category", callback_data="admin_add_category")],
        [InlineKeyboardButton("🔙 Back to Content Management", callback_data="admin_content")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📂 Category Management\n"
        "Select a category to edit or add a new one:",
        reply_markup=reply_markup
    )

@admin_required
async def admin_add_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding a new category"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "Please provide category details:\n"
        "1. Name\n"
        "2. Description\n"
        "3. Content Type (video/book)\n\n"
        "Format your response as:\n"
        "Name: [category name]\n"
        "Description: [description]\n"
        "Content Type: [video/book]"
    )
    
    # Set conversation state
    context.user_data['category_state'] = 'waiting_for_details'

async def admin_category_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category details input"""
    # Check if we're in category state
    if context.user_data.get('category_state') != 'waiting_for_details':
        return
    
    # Parse category details from message
    message_text = update.message.text
    lines = message_text.split('\n')
    
    category_data = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            category_data[key.strip().lower()] = value.strip()
    
    # Validate required fields
    required_fields = ['name', 'content type']
    missing_fields = [field for field in required_fields if field not in category_data]
    
    if missing_fields:
        await update.message.reply_text(
            f"Missing required fields: {', '.join(missing_fields)}\n"
            f"Please provide all required information."
        )
        return
    
    # Validate content type
    content_type = category_data['content type'].lower()
    if content_type not in ['video', 'book']:
        await update.message.reply_text("Content type must be 'video' or 'book'.")
        return
    
    # Create category
    try:
        category = Category(
            name=category_data['name'],
            description=category_data.get('description', ''),
            content_type=content_type
        )
        
        session.add(category)
        session.commit()
        
        await update.message.reply_text(
            f"✅ Category created successfully!\n"
            f"Name: {category.name}\n"
            f"Type: {category.content_type}\n"
            f"ID: {category.id}"
        )
        
        # Clear category state
        context.user_data.pop('category_state', None)
        
    except Exception as e:
        logger.error(f"Error creating category: {str(e)}")
        await update.message.reply_text(
            "Error creating category. Please try again."
        )
```

## User Management

### Admin User Handler
```python
@admin_required
async def admin_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin user management"""
    keyboard = [
        [InlineKeyboardButton("👥 List Users", callback_data="admin_list_users")],
        [InlineKeyboardButton("🔍 Search Users", callback_data="admin_search_users")],
        [InlineKeyboardButton("📝 User Details", callback_data="admin_user_details")],
        [InlineKeyboardButton("💬 Message Users", callback_data="admin_message_users")],
        [InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👥 User Management\n"
        "Select an action:",
        reply_markup=reply_markup
    )

@admin_required
async def admin_list_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle listing users"""
    query = update.callback_query
    await query.answer()
    
    # Get users (limit to 10 for now)
    users = session.query(User).limit(10).all()
    
    if not users:
        await query.edit_message_text(
            "No users found.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="admin_users")
            ]])
        )
        return
    
    # Create user list
    user_list = "👥 Users:\n\n"
    for user in users:
        status = "✅" if user.is_active else "❌"
        admin_status = "👑" if user.is_admin else ""
        user_list += f"{status}{admin_status} {user.first_name} {user.last_name or ''} (@{user.username or 'N/A'})\n"
        user_list += f"  ID: {user.telegram_id}\n"
        user_list += f"  Registered: {user.registration_date.strftime('%Y-%m-%d')}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_users")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(user_list, reply_markup=reply_markup)
```

## Subscription Management

### Admin Subscription Handler
```python
@admin_required
async def admin_subscriptions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin subscription management"""
    keyboard = [
        [InlineKeyboardButton("📋 Subscription Plans", callback_data="admin_subscription_plans")],
        [InlineKeyboardButton("💳 User Subscriptions", callback_data="admin_user_subscriptions")],
        [InlineKeyboardButton("💰 Payment Management", callback_data="admin_payments")],
        [InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💳 Subscription Management\n"
        "Select an action:",
        reply_markup=reply_markup
    )

@admin_required
async def admin_subscription_plans_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription plans management"""
    query = update.callback_query
    await query.answer()
    
    # Get all subscription plans
    plans = session.query(SubscriptionPlan).all()
    
    keyboard = []
    
    for plan in plans:
        status = "✅" if plan.is_active else "❌"
        button_text = f"{status} {plan.name} (${plan.price_monthly}/month)"
        callback_data = f"admin_edit_plan_{plan.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Add action buttons
    keyboard.extend([
        [InlineKeyboardButton("➕ Add New Plan", callback_data="admin_add_plan")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_subscriptions")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    plan_list = "📋 Subscription Plans:\n\n"
    for plan in plans:
        status = "✅ Active" if plan.is_active else "❌ Inactive"
        plan_list += f"{status} {plan.name}\n"
        plan_list += f"  Monthly: ${plan.price_monthly}\n"
        plan_list += f"  Yearly: ${plan.price_yearly}\n"
        plan_list += f"  Duration: {plan.duration_days} days\n\n"
    
    await query.edit_message_text(
        plan_list,
        reply_markup=reply_markup
    )
```

## Analytics and Reporting

### Admin Analytics Handler
```python
@admin_required
async def admin_analytics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin analytics"""
    keyboard = [
        [InlineKeyboardButton("📈 Dashboard", callback_data="admin_analytics_dashboard")],
        [InlineKeyboardButton("📚 Content Performance", callback_data="admin_analytics_content")],
        [InlineKeyboardButton("👥 User Engagement", callback_data="admin_analytics_users")],
        [InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📊 Analytics and Reporting\n"
        "Select an action:",
        reply_markup=reply_markup
    )

@admin_required
async def admin_analytics_dashboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle analytics dashboard"""
    query = update.callback_query
    await query.answer()
    
    # Get analytics data
    total_users = session.query(User).count()
    active_subscriptions = session.query(Subscription).filter(
        Subscription.is_active == True,
        Subscription.end_date > datetime.utcnow()
    ).count()
    
    total_content = session.query(Content).count()
    total_videos = session.query(Content).filter(Content.content_type == "video").count()
    total_books = session.query(Content).filter(Content.content_type == "book").count()
    
    # Get recent activity
    recent_users = session.query(User).order_by(User.registration_date.desc()).limit(5).all()
    recent_content = session.query(Content).order_by(Content.upload_date.desc()).limit(5).all()
    
    # Format dashboard text
    dashboard_text = "📈 Analytics Dashboard\n\n"
    dashboard_text += f"👥 Total Users: {total_users}\n"
    dashboard_text += f"💳 Active Subscriptions: {active_subscriptions}\n"
    dashboard_text += f"📚 Total Content: {total_content}\n"
    dashboard_text += f"  📹 Videos: {total_videos}\n"
    dashboard_text += f"  📚 Books: {total_books}\n\n"
    
    dashboard_text += "🆕 Recent Users:\n"
    for user in recent_users:
        dashboard_text += f"  {user.first_name} {user.last_name or ''} (@{user.username or 'N/A'})\n"
    
    dashboard_text += "\n🆕 Recent Content:\n"
    for content in recent_content:
        dashboard_text += f"  {content.title} ({content.content_type})\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_analytics")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(dashboard_text, reply_markup=reply_markup)
```

## Notification System

### Admin Notification Handler
```python
@admin_required
async def admin_notifications_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin notifications"""
    keyboard = [
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👤 Individual Notification", callback_data="admin_notify_user")],
        [InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔔 Notification System\n"
        "Select an action:",
        reply_markup=reply_markup
    )

@admin_required
async def admin_broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast message"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "Please enter the broadcast message you want to send to all users.\n"
        "The message will be sent to all registered users."
    )
    
    # Set conversation state
    context.user_data['notification_state'] = 'waiting_for_broadcast_message'

async def admin_broadcast_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast message input"""
    # Check if we're in notification state
    if context.user_data.get('notification_state') != 'waiting_for_broadcast_message':
        return
    
    message_text = update.message.text
    
    # Get all users
    users = session.query(User).all()
    
    success_count = 0
    error_count = 0
    
    # Send message to each user
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user.telegram_id,
                text=f"📢 Broadcast Message:\n\n{message_text}"
            )
            
            # Create notification record
            notification = Notification(
                user_id=user.id,
                title="Broadcast Message",
                message=message_text,
                notification_type="broadcast"
            )
            session.add(notification)
            success_count += 1
            
        except Exception as e:
            logger.error(f"Error sending broadcast to user {user.telegram_id}: {str(e)}")
            error_count += 1
    
    session.commit()
    
    await update.message.reply_text(
        f"✅ Broadcast message sent!\n"
        f"Successful: {success_count}\n"
        f"Errors: {error_count}"
    )
    
    # Clear notification state
    context.user_data.pop('notification_state', None)
```

## Admin Main Menu

### Admin Main Handler
```python
@admin_required
async def admin_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main admin menu"""
    keyboard = [
        [InlineKeyboardButton("📚 Content Management", callback_data="admin_content")],
        [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
        [InlineKeyboardButton("💳 Subscription Management", callback_data="admin_subscriptions")],
        [InlineKeyboardButton("📊 Analytics", callback_data="admin_analytics")],
        [InlineKeyboardButton("🔔 Notifications", callback_data="admin_notifications")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👑 Admin Panel\n"
        "Select a section to manage:",
        reply_markup=reply_markup
    )
```

## Error Handling and Security

### Security Considerations
1. All admin commands are protected with the `@admin_required` decorator
2. Admin actions are logged for audit purposes
3. Sensitive operations require confirmation
4. File uploads are validated for type and size
5. Database operations use parameterized queries to prevent SQL injection

### Error Handling
1. Invalid admin commands show help text
2. Unauthorized access attempts are logged
3. Database errors show user-friendly messages while logging technical details
4. File upload errors provide clear feedback to admin
5. Network issues with Telegram are retried with exponential backoff

## Future Enhancements
1. Web-based admin panel as an alternative to Telegram interface
2. Role-based access control (multiple admin levels)
3. Automated reporting and alerting systems
4. Integration with external analytics platforms
5. API access for third-party integrations
6. Bulk user management operations
7. Advanced content analytics and insights
8. User segmentation for targeted notifications