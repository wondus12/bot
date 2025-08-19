# Database Schema Design

## 1. Users Table
Stores user information and authentication data.

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active DATETIME,
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE
);
```

## 2. Subscription Plans Table
Defines the available subscription plans.

```sql
CREATE TABLE subscription_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price_monthly REAL NOT NULL,
    price_yearly REAL NOT NULL,
    duration_days INTEGER NOT NULL, -- 30 for monthly, 365 for yearly
    is_active BOOLEAN DEFAULT TRUE
);
```

## 3. User Subscriptions Table
Tracks user subscription status and history.

```sql
CREATE TABLE user_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    plan_id INTEGER NOT NULL,
    start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_date DATETIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    payment_id TEXT, -- Telegram payment ID
    payment_status TEXT, -- pending, completed, failed, refunded
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (plan_id) REFERENCES subscription_plans (id)
);
```

## 4. Categories Table
Organizes content into categories.

```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    content_type TEXT NOT NULL, -- 'video' or 'book'
    is_active BOOLEAN DEFAULT TRUE
);
```

## 5. Content Table
Stores metadata for videos and books.

```sql
CREATE TABLE content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category_id INTEGER NOT NULL,
    content_type TEXT NOT NULL, -- 'video' or 'book'
    file_path TEXT, -- Local file path or URL
    thumbnail_path TEXT, -- For videos
    duration INTEGER, -- For videos in seconds
    page_count INTEGER, -- For books
    author TEXT, -- For books
    publisher TEXT, -- For books
    publication_date DATE, -- For books
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_premium BOOLEAN DEFAULT FALSE, -- Free or premium content
    is_active BOOLEAN DEFAULT TRUE,
    view_count INTEGER DEFAULT 0,
    download_count INTEGER DEFAULT 0,
    FOREIGN KEY (category_id) REFERENCES categories (id)
);
```

## 6. User Content Interactions Table
Tracks user interactions with content.

```sql
CREATE TABLE user_content_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    content_id INTEGER NOT NULL,
    interaction_type TEXT NOT NULL, -- 'view', 'download', 'rate', 'review'
    interaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    rating INTEGER, -- 1-5 stars
    review TEXT, -- User review text
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (content_id) REFERENCES content (id),
    UNIQUE(user_id, content_id, interaction_type)
);
```

## 7. Referrals Table
Tracks user referral relationships.

```sql
CREATE TABLE referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,
    referred_id INTEGER NOT NULL,
    referral_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    reward_claimed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (referrer_id) REFERENCES users (id),
    FOREIGN KEY (referred_id) REFERENCES users (id),
    UNIQUE(referred_id)
);
```

## 8. Notifications Table
Stores notifications sent to users.

```sql
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    notification_type TEXT NOT NULL, -- 'new_content', 'subscription_reminder', etc.
    is_read BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);