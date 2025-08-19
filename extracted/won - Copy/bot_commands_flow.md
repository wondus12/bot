# Bot Commands and User Flow

## User Commands

### Authentication & Registration
- `/start` - Welcome message and initial setup
- `/register` - Register as a new user
- `/profile` - View user profile and subscription status

### Subscription Management
- `/subscribe` - View subscription plans and subscribe
- `/subscription` - View current subscription details
- `/cancel_subscription` - Cancel current subscription

### Content Access
- `/library` - Browse content library
- `/search` - Search for specific content
- `/categories` - Browse content by categories
- `/downloads` - View downloaded content history
- `/recent` - View recently added content

### User Interaction
- `/rate` - Rate content
- `/review` - Write a review for content
- `/notifications` - View notifications
- `/referral` - Get referral link and rewards

### Help & Support
- `/help` - Show help information
- `/contact` - Contact support/admin

## Admin Commands
- `/admin` - Access admin panel
- `/upload_content` - Upload new content
- `/delete_content` - Delete existing content
- `/manage_categories` - Add/edit/delete categories
- `/user_management` - Manage user accounts
- `/subscription_management` - Manage subscriptions
- `/analytics` - View analytics and reports
- `/send_notification` - Send notification to users

## User Flow

### New User Flow
1. User starts the bot with `/start`
2. Bot sends welcome message with brief description
3. User registers with `/register` if not already registered
4. User can browse free content immediately
5. User can subscribe with `/subscribe` to access premium content

### Content Browsing Flow
1. User accesses library with `/library`
2. Bot displays categories
3. User selects a category
4. Bot displays content in that category
5. User selects content to view details
6. If content is premium, check user subscription
7. Provide download/streaming link or deny access

### Subscription Flow
1. User uses `/subscribe` command
2. Bot displays subscription plans
3. User selects a plan (monthly/yearly)
4. Bot initiates Telegram payment process
5. User completes payment
6. Bot confirms subscription and grants access

### Content Interaction Flow
1. User views content details
2. User can rate content with stars
3. User can write a review
4. User can download/stream content
5. Bot tracks user interactions for analytics

## Command Implementation Details

### /start
```
Handler: start_handler
Description: Welcome message and initial setup
Flow:
1. Check if user exists in database
2. If not, prompt for registration
3. If yes, show main menu with keyboard buttons
4. Display available commands based on user role (user/admin)
```

### /register
```
Handler: register_handler
Description: Register as a new user
Flow:
1. Check if user is already registered
2. If yes, inform user they're already registered
3. If no, collect user information (Telegram ID, username, name)
4. Create user record in database
5. Send confirmation message
```

### /subscribe
```
Handler: subscribe_handler
Description: View subscription plans and subscribe
Flow:
1. Retrieve active subscription plans from database
2. Display plans with pricing and features
3. User selects a plan
4. Initiate Telegram payment
5. On successful payment, create subscription record
6. Update user's subscription status
7. Send confirmation with expiration date
```

### /library
```
Handler: library_handler
Description: Browse content library
Flow:
1. Display content categories
2. User selects a category
3. Show content items in category
4. User selects content item
5. Display content details (title, description, rating, etc.)
6. Provide download/streaming option based on user's subscription
```

### /search
```
Handler: search_handler
Description: Search for specific content
Flow:
1. Prompt user for search query
2. Search content titles, descriptions, and tags
3. Display matching results
4. User selects content to view details
```

### /profile
```
Handler: profile_handler
Description: View user profile and subscription status
Flow:
1. Retrieve user information from database
2. Display user details (name, registration date)
3. Show subscription status (active/inactive, expiration date)
4. Show content interaction statistics
```

## User Interface Design

### Main Menu (Reply Keyboard)
```
[📚 Library] [🔍 Search]
[👤 Profile] [💳 Subscribe]
[🔔 Notifications] [🎁 Referral]
[❓ Help]
```

### Admin Menu (Reply Keyboard)
```
[📚 Manage Content] [📊 Analytics]
[👥 User Management] [💳 Subscription Management]
[🔔 Send Notification] [⚙️ Settings]
[❓ Help]
```

## Error Handling

### Common Error Scenarios
1. User tries to access premium content without subscription
   - Response: "This content is only available to premium subscribers. Use /subscribe to get access."

2. User tries to subscribe but already has an active subscription
   - Response: "You already have an active subscription. Use /subscription to view details."

3. User tries to rate content they haven't accessed
   - Response: "You need to view this content before rating it."

4. User tries to use admin commands without admin privileges
   - Response: "You don't have permission to use this command."

## State Management

The bot will use conversation handlers to manage multi-step interactions:

1. Subscription process (payment confirmation)
2. Content upload process (admin)
3. Search refinement
4. Review submission

Each conversation will maintain state using Telegram's built-in context system to track:
- Current step in the conversation
- User data collected so far
- Selected options
- Temporary data needed for the interaction