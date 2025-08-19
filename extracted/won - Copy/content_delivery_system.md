# Content Delivery System Implementation

## Overview
This document outlines the implementation details for the content delivery system that will handle videos and books in the Telegram bot. This system will enable users to browse, search, and access content based on their subscription status.

## Content Model Structure

### Content Model
```python
class Content(Base):
    __tablename__ = 'content'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    content_type = Column(String, nullable=False)  # 'video' or 'book'
    file_path = Column(String)  # Local file path or URL
    thumbnail_path = Column(String)  # For videos
    duration = Column(Integer)  # For videos in seconds
    page_count = Column(Integer)  # For books
    author = Column(String)  # For books
    publisher = Column(String)  # For books
    publication_date = Column(Date)  # For books
    upload_date = Column(DateTime, default=datetime.utcnow)
    is_premium = Column(Boolean, default=False)  # Free or premium content
    is_active = Column(Boolean, default=True)
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    
    # Relationships
    category = relationship("Category", back_populates="content")
    interactions = relationship("UserInteraction", back_populates="content")

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    content_type = Column(String, nullable=False)  # 'video' or 'book'
    is_active = Column(Boolean, default=True)
    
    # Relationships
    content = relationship("Content", back_populates="category")
```

## Content Service Implementation

### Content Service
```python
class ContentService:
    @staticmethod
    async def get_categories(content_type=None):
        """Get all active categories, optionally filtered by content type"""
        query = session.query(Category).filter(Category.is_active == True)
        if content_type:
            query = query.filter(Category.content_type == content_type)
        return query.all()
    
    @staticmethod
    async def get_content_by_category(category_id, is_premium=None):
        """Get content by category, optionally filtered by premium status"""
        query = session.query(Content).filter(
            Content.category_id == category_id,
            Content.is_active == True
        )
        if is_premium is not None:
            query = query.filter(Content.is_premium == is_premium)
        return query.all()
    
    @staticmethod
    async def search_content(query_text, content_type=None):
        """Search content by title or description"""
        query = session.query(Content).filter(
            or_(
                Content.title.contains(query_text),
                Content.description.contains(query_text)
            ),
            Content.is_active == True
        )
        if content_type:
            query = query.filter(Content.content_type == content_type)
        return query.all()
    
    @staticmethod
    async def get_content_details(content_id):
        """Get detailed information about specific content"""
        return session.query(Content).filter(
            Content.id == content_id,
            Content.is_active == True
        ).first()
    
    @staticmethod
    async def get_recent_content(limit=10, content_type=None):
        """Get recently uploaded content"""
        query = session.query(Content).filter(Content.is_active == True)
        if content_type:
            query = query.filter(Content.content_type == content_type)
        return query.order_by(Content.upload_date.desc()).limit(limit).all()
    
    @staticmethod
    async def increment_view_count(content_id):
        """Increment view count for content"""
        content = session.query(Content).get(content_id)
        if content:
            content.view_count += 1
            session.commit()
    
    @staticmethod
    async def increment_download_count(content_id):
        """Increment download count for content"""
        content = session.query(Content).get(content_id)
        if content:
            content.download_count += 1
            session.commit()
```

## Library Handler Implementation

### Library Handler
```python
async def library_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle library command - show content categories"""
    # Get all active categories for both videos and books
    video_categories = await ContentService.get_categories(content_type="video")
    book_categories = await ContentService.get_categories(content_type="book")
    
    # Create inline keyboard with categories
    keyboard = []
    
    if video_categories:
        keyboard.append([InlineKeyboardButton("📹 Videos", callback_data="library_videos")])
        for category in video_categories:
            button_text = f"  📁 {category.name}"
            callback_data = f"category_{category.id}_video"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    if book_categories:
        keyboard.append([InlineKeyboardButton("📚 Books", callback_data="library_books")])
        for category in book_categories:
            button_text = f"  📁 {category.name}"
            callback_data = f"category_{category.id}_book"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📚 Content Library\n"
        "Select a category to browse content:",
        reply_markup=reply_markup
    )

async def library_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle library category selection"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "library_videos":
        # Show video categories
        categories = await ContentService.get_categories(content_type="video")
        await show_categories(query, categories, "video")
    elif data == "library_books":
        # Show book categories
        categories = await ContentService.get_categories(content_type="book")
        await show_categories(query, categories, "book")
    elif data.startswith("category_"):
        # Parse category data
        parts = data.split("_")
        if len(parts) == 4:
            category_id = int(parts[1])
            content_type = parts[3]
            await show_content_in_category(query, category_id, content_type)

async def show_categories(query, categories, content_type):
    """Show categories for a specific content type"""
    keyboard = []
    
    for category in categories:
        button_text = f"📁 {category.name}"
        callback_data = f"category_{category.id}_{content_type}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="library_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    content_type_text = "Videos" if content_type == "video" else "Books"
    await query.edit_message_text(
        f"Select a {content_type_text} category:",
        reply_markup=reply_markup
    )

async def show_content_in_category(query, category_id, content_type):
    """Show content in a specific category"""
    # Get category name
    category = session.query(Category).get(category_id)
    if not category:
        await query.edit_message_text("Category not found.")
        return
    
    # Get content in category
    content_items = await ContentService.get_content_by_category(category_id)
    
    if not content_items:
        await query.edit_message_text(
            f"No content found in category '{category.name}'.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="library_main")
            ]])
        )
        return
    
    # Create keyboard with content items
    keyboard = []
    
    for content in content_items:
        # Add premium indicator if needed
        premium_indicator = "💎 " if content.is_premium else ""
        button_text = f"{premium_indicator}{content.title}"
        callback_data = f"content_{content.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"library_{content_type}s")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Content in '{category.name}' category:",
        reply_markup=reply_markup
    )
```

## Content Details Handler

### Content Details Handler
```python
async def content_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle content details view"""
    query = update.callback_query
    await query.answer()
    
    # Parse content ID from callback data
    data_parts = query.data.split("_")
    if len(data_parts) != 2 or data_parts[0] != "content":
        await query.edit_message_text("Invalid content selection.")
        return
    
    content_id = int(data_parts[1])
    
    # Get content details
    content = await ContentService.get_content_details(content_id)
    if not content:
        await query.edit_message_text("Content not found.")
        return
    
    # Check if user has access to premium content
    telegram_id = query.from_user.id
    has_access = True
    
    if content.is_premium:
        active_subscription = await SubscriptionService.get_active_subscription(telegram_id)
        has_access = active_subscription is not None
    
    # Format content details
    content_type_text = "Video" if content.content_type == "video" else "Book"
    details_text = f"📹 {content_type_text}: {content.title}\n\n"
    details_text += f"📁 Category: {content.category.name}\n"
    details_text += f"📝 Description: {content.description}\n"
    
    if content.content_type == "video":
        if content.duration:
            minutes, seconds = divmod(content.duration, 60)
            details_text += f"⏱ Duration: {minutes}m {seconds}s\n"
    else:  # book
        if content.author:
            details_text += f"✍️ Author: {content.author}\n"
        if content.page_count:
            details_text += f"📄 Pages: {content.page_count}\n"
        if content.publisher:
            details_text += f"🏢 Publisher: {content.publisher}\n"
        if content.publication_date:
            details_text += f"📅 Published: {content.publication_date.strftime('%Y-%m-%d')}\n"
    
    details_text += f"👁 Views: {content.view_count}\n"
    details_text += f"📥 Downloads: {content.download_count}\n"
    
    if content.is_premium and not has_access:
        details_text += f"\n💎 This is premium content.\n"
        details_text += f"Subscribe to access this content.\n"
        details_text += f"Use /subscribe to get access."
        
        keyboard = [[InlineKeyboardButton("💳 Subscribe", callback_data="subscribe_start")]]
    else:
        # Provide access to content
        if content.content_type == "video":
            details_text += f"\n▶️ Ready to watch this video?"
        else:
            details_text += f"\n📖 Ready to read this book?"
            
        keyboard = [
            [InlineKeyboardButton("📥 Access Content", callback_data=f"access_{content.id}")],
            [InlineKeyboardButton("⭐ Rate Content", callback_data=f"rate_{content.id}")]
        ]
    
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"category_{content.category_id}_{content.content_type}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(details_text, reply_markup=reply_markup)

async def access_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle content access request"""
    query = update.callback_query
    await query.answer()
    
    # Parse content ID from callback data
    data_parts = query.data.split("_")
    if len(data_parts) != 2 or data_parts[0] != "access":
        await query.edit_message_text("Invalid access request.")
        return
    
    content_id = int(data_parts[1])
    
    # Get content details
    content = await ContentService.get_content_details(content_id)
    if not content:
        await query.edit_message_text("Content not found.")
        return
    
    # Increment view count
    await ContentService.increment_view_count(content_id)
    
    # Send content file
    try:
        if content.content_type == "video":
            # For videos, send as document (or use streaming URL if available)
            if content.file_path and os.path.exists(content.file_path):
                await query.message.reply_video(
                    open(content.file_path, 'rb'),
                    caption=f"📹 {content.title}\n\n{content.description}"
                )
            else:
                await query.message.reply_text("Video file not available.")
        else:  # book
            # For books, send as document
            if content.file_path and os.path.exists(content.file_path):
                await query.message.reply_document(
                    open(content.file_path, 'rb'),
                    caption=f"📚 {content.title}\n\n{content.description}"
                )
                # Increment download count
                await ContentService.increment_download_count(content_id)
            else:
                await query.message.reply_text("Book file not available.")
        
        # Record user interaction
        telegram_id = query.from_user.id
        user = UserService.get_user(telegram_id)
        if user:
            interaction = UserInteraction(
                user_id=user.id,
                content_id=content_id,
                interaction_type="view" if content.content_type == "video" else "download"
            )
            session.add(interaction)
            session.commit()
            
    except Exception as e:
        logger.error(f"Error sending content: {str(e)}")
        await query.message.reply_text("Error accessing content. Please try again later.")
```

## Search Handler Implementation

### Search Handler
```python
async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle search command"""
    # If no search query provided, prompt user
    if not context.args:
        await update.message.reply_text(
            "Please provide a search query.\n"
            "Usage: /search <query>\n"
            "Example: /search python programming"
        )
        return
    
    query_text = " ".join(context.args)
    
    # Search for content
    results = await ContentService.search_content(query_text)
    
    if not results:
        await update.message.reply_text(f"No content found for '{query_text}'.")
        return
    
    # Create keyboard with search results
    keyboard = []
    
    for content in results[:10]:  # Limit to 10 results
        # Add premium indicator if needed
        premium_indicator = "💎 " if content.is_premium else ""
        content_type_indicator = "📹 " if content.content_type == "video" else "📚 "
        button_text = f"{premium_indicator}{content_type_indicator}{content.title}"
        callback_data = f"content_{content.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Search results for '{query_text}':",
        reply_markup=reply_markup
    )

async def recent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle recent command - show recently added content"""
    # Get recent content
    recent_content = await ContentService.get_recent_content(limit=10)
    
    if not recent_content:
        await update.message.reply_text("No recent content found.")
        return
    
    # Create keyboard with recent content
    keyboard = []
    
    for content in recent_content:
        # Add premium indicator if needed
        premium_indicator = "💎 " if content.is_premium else ""
        content_type_indicator = "📹 " if content.content_type == "video" else "📚 "
        button_text = f"{premium_indicator}{content_type_indicator}{content.title}"
        callback_data = f"content_{content.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Recently added content:",
        reply_markup=reply_markup
    )
```

## File Management Utilities

### File Utilities
```python
class FileUtils:
    @staticmethod
    def save_uploaded_file(file, content_type, category_name):
        """Save uploaded file to appropriate directory"""
        # Determine base directory based on content type
        if content_type == "video":
            base_dir = "data/videos"
        else:  # book
            base_dir = "data/books"
        
        # Create category directory if it doesn't exist
        category_dir = os.path.join(base_dir, category_name.lower().replace(" ", "_"))
        os.makedirs(category_dir, exist_ok=True)
        
        # Generate unique filename
        filename = f"{int(time.time())}_{file.file_name}"
        file_path = os.path.join(category_dir, filename)
        
        # Save file
        file.download(file_path)
        
        return file_path
    
    @staticmethod
    def delete_content_file(file_path):
        """Delete content file from storage"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {str(e)}")
        return False
    
    @staticmethod
    def get_file_size(file_path):
        """Get file size in bytes"""
        if os.path.exists(file_path):
            return os.path.getsize(file_path)
        return 0
    
    @staticmethod
    def is_valid_file_type(file_path, content_type):
        """Check if file type is valid for content type"""
        if content_type == "video":
            # Accept common video formats
            valid_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']
        else:  # book
            # Accept common document formats
            valid_extensions = ['.pdf', '.epub', '.mobi', '.txt']
        
        _, extension = os.path.splitext(file_path.lower())
        return extension in valid_extensions
```

## Content Validation and Processing

### Content Validation
```python
class ContentValidator:
    @staticmethod
    def validate_content_data(title, description, category_id, content_type):
        """Validate content data before creation"""
        errors = []
        
        if not title or len(title.strip()) == 0:
            errors.append("Title is required")
        
        if len(title) > 200:
            errors.append("Title must be less than 200 characters")
        
        if not description or len(description.strip()) == 0:
            errors.append("Description is required")
        
        if len(description) > 1000:
            errors.append("Description must be less than 1000 characters")
        
        if not category_id:
            errors.append("Category is required")
        
        if content_type not in ['video', 'book']:
            errors.append("Invalid content type")
        
        return errors
    
    @staticmethod
    def extract_video_metadata(file_path):
        """Extract metadata from video file"""
        # This would require additional libraries like ffmpeg-python
        # For now, we'll return placeholder values
        return {
            'duration': 0,  # in seconds
            'thumbnail_path': None
        }
    
    @staticmethod
    def extract_book_metadata(file_path):
        """Extract metadata from book file"""
        # This would require additional libraries like PyPDF2 for PDFs
        # For now, we'll return placeholder values
        return {
            'page_count': 0,
            'author': None,
            'publisher': None,
            'publication_date': None
        }
```

## Error Handling and User Feedback

### Error Handling
1. Content not found - Show appropriate message
2. File not available - Log error and notify user
3. Invalid file type - Reject upload with explanation
4. File size limits - Check and enforce limits
5. Database errors - Log and show user-friendly messages
6. Network errors - Retry mechanisms for file operations

## Future Enhancements

1. Content streaming for videos instead of direct file download
2. Content recommendations based on user history
3. Content bookmarking feature
4. Offline content access
5. Content sharing functionality
6. Advanced search with filters (date range, rating, etc.)
7. Content reporting for inappropriate material
8. Batch upload functionality for admins