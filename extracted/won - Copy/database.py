# Database initialization and session management
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base
from models.user import User
from models.subscription import Subscription
from models.subscription_plan import SubscriptionPlan
from models.content import Content
from datetime import datetime, timedelta
from config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_database():
    """Initialize database tables with comprehensive sample data"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        session = SessionLocal()
        try:
            # Create subscription plans if they don't exist
            existing_plans = session.query(SubscriptionPlan).count()
            if existing_plans == 0:
                # Create subscription plans with 100 ETB pricing
                plans = [
                    SubscriptionPlan(
                        name="Basic Monthly",
                        description="Access to basic content for 1 month",
                        price_monthly=100.0,
                        price_yearly=1000.0,
                        duration_days=30,
                        is_active=True
                    ),
                    SubscriptionPlan(
                        name="Premium Monthly",
                        description="Access to all premium content for 1 month",
                        price_monthly=200.0,
                        price_yearly=2000.0,
                        duration_days=30,
                        is_active=True
                    ),
                    SubscriptionPlan(
                        name="Basic Yearly",
                        description="Access to basic content for 1 year (2 months free!)",
                        price_monthly=100.0,
                        price_yearly=1000.0,
                        duration_days=365,
                        is_active=True
                    ),
                    SubscriptionPlan(
                        name="Premium Yearly",
                        description="Access to all premium content for 1 year (4 months free!)",
                        price_monthly=200.0,
                        price_yearly=1600.0,
                        duration_days=365,
                        is_active=True
                    ),
                    SubscriptionPlan(
                        name="Weekly Trial",
                        description="7-day trial access to all content",
                        price_monthly=50.0,
                        price_yearly=500.0,
                        duration_days=7,
                        is_active=True
                    )
                ]
                
                for plan in plans:
                    session.add(plan)
                session.commit()
                logger.info("Subscription plans created successfully")
            
            # Create sample users if they don't exist
            existing_users = session.query(User).count()
            if existing_users == 0:
                sample_users = [
                    User(
                        telegram_id=123456789,
                        username="john_doe",
                        first_name="John",
                        last_name="Doe",
                        email="john@example.com",
                        is_admin=True,
                        registration_date=datetime.utcnow() - timedelta(days=30)
                    ),
                    User(
                        telegram_id=987654321,
                        username="jane_smith",
                        first_name="Jane",
                        last_name="Smith",
                        email="jane@example.com",
                        registration_date=datetime.utcnow() - timedelta(days=15)
                    ),
                    User(
                        telegram_id=555666777,
                        username="alex_wilson",
                        first_name="Alex",
                        last_name="Wilson",
                        registration_date=datetime.utcnow() - timedelta(days=5)
                    ),
                    User(
                        telegram_id=111222333,
                        username="sarah_johnson",
                        first_name="Sarah",
                        last_name="Johnson",
                        email="sarah@example.com",
                        registration_date=datetime.utcnow() - timedelta(days=2)
                    )
                ]
                
                for user in sample_users:
                    session.add(user)
                session.commit()
                logger.info("Sample users created successfully")
            
            # Create sample content if it doesn't exist
            existing_content = session.query(Content).count()
            if existing_content == 0:
                sample_content = [
                    # Video Content
                    Content(
                        title="Introduction to Python Programming",
                        description="Complete beginner's guide to Python programming with practical examples",
                        content_type="video",
                        file_path="/content/videos/python_intro.mp4",
                        file_size=1024000000,  # 1GB
                        duration=3600.0,  # 1 hour
                        thumbnail_path="/content/thumbnails/python_intro.jpg",
                        encryption_key_id="key_001",
                        created_date=datetime.utcnow() - timedelta(days=20)
                    ),
                    Content(
                        title="Advanced Web Development",
                        description="Master modern web development with React, Node.js, and databases",
                        content_type="video",
                        file_path="/content/videos/web_dev_advanced.mp4",
                        file_size=2048000000,  # 2GB
                        duration=7200.0,  # 2 hours
                        thumbnail_path="/content/thumbnails/web_dev.jpg",
                        encryption_key_id="key_002",
                        created_date=datetime.utcnow() - timedelta(days=15)
                    ),
                    Content(
                        title="Data Science Fundamentals",
                        description="Learn data analysis, visualization, and machine learning basics",
                        content_type="video",
                        file_path="/content/videos/data_science.mp4",
                        file_size=1536000000,  # 1.5GB
                        duration=5400.0,  # 1.5 hours
                        thumbnail_path="/content/thumbnails/data_science.jpg",
                        encryption_key_id="key_003",
                        created_date=datetime.utcnow() - timedelta(days=10)
                    ),
                    
                    # PDF/Book Content
                    Content(
                        title="Clean Code: A Handbook of Agile Software Craftsmanship",
                        description="Essential guide to writing clean, maintainable code",
                        content_type="pdf",
                        file_path="/content/books/clean_code.pdf",
                        file_size=15000000,  # 15MB
                        thumbnail_path="/content/thumbnails/clean_code.jpg",
                        encryption_key_id="key_004",
                        created_date=datetime.utcnow() - timedelta(days=25)
                    ),
                    Content(
                        title="Design Patterns: Elements of Reusable Object-Oriented Software",
                        description="The classic book on software design patterns",
                        content_type="pdf",
                        file_path="/content/books/design_patterns.pdf",
                        file_size=20000000,  # 20MB
                        thumbnail_path="/content/thumbnails/design_patterns.jpg",
                        encryption_key_id="key_005",
                        created_date=datetime.utcnow() - timedelta(days=18)
                    ),
                    Content(
                        title="The Pragmatic Programmer",
                        description="Your journey to mastery in software development",
                        content_type="pdf",
                        file_path="/content/books/pragmatic_programmer.pdf",
                        file_size=12000000,  # 12MB
                        thumbnail_path="/content/thumbnails/pragmatic_programmer.jpg",
                        encryption_key_id="key_006",
                        created_date=datetime.utcnow() - timedelta(days=12)
                    ),
                    
                    # Audio Content
                    Content(
                        title="Tech Podcast: Future of AI",
                        description="Discussion on artificial intelligence trends and future developments",
                        content_type="audio",
                        file_path="/content/audio/ai_podcast.mp3",
                        file_size=50000000,  # 50MB
                        duration=2700.0,  # 45 minutes
                        thumbnail_path="/content/thumbnails/ai_podcast.jpg",
                        encryption_key_id="key_007",
                        created_date=datetime.utcnow() - timedelta(days=7)
                    ),
                    Content(
                        title="Startup Success Stories",
                        description="Interviews with successful entrepreneurs and their journey",
                        content_type="audio",
                        file_path="/content/audio/startup_stories.mp3",
                        file_size=75000000,  # 75MB
                        duration=4500.0,  # 75 minutes
                        thumbnail_path="/content/thumbnails/startup_stories.jpg",
                        encryption_key_id="key_008",
                        created_date=datetime.utcnow() - timedelta(days=3)
                    )
                ]
                
                for content in sample_content:
                    session.add(content)
                session.commit()
                logger.info("Sample content created successfully")
            
            # Create sample subscriptions
            existing_subscriptions = session.query(Subscription).count()
            if existing_subscriptions == 0:
                # Get created plans and users
                plans = session.query(SubscriptionPlan).all()
                users = session.query(User).all()
                
                if plans and users and len(users) >= 3 and len(plans) >= 5:
                    sample_subscriptions = [
                        Subscription(
                            user_id=users[0].id,  # John Doe - Admin
                            plan_id=plans[1].id,  # Premium Monthly
                            start_date=datetime.utcnow() - timedelta(days=15),
                            end_date=datetime.utcnow() + timedelta(days=15),
                            payment_id="pay_001",
                            payment_status="completed"
                        ),
                        Subscription(
                            user_id=users[1].id,  # Jane Smith
                            plan_id=plans[0].id,  # Basic Monthly
                            start_date=datetime.utcnow() - timedelta(days=10),
                            end_date=datetime.utcnow() + timedelta(days=20),
                            payment_id="pay_002",
                            payment_status="completed"
                        ),
                        Subscription(
                            user_id=users[2].id,  # Alex Wilson
                            plan_id=plans[4].id,  # Weekly Trial
                            start_date=datetime.utcnow() - timedelta(days=3),
                            end_date=datetime.utcnow() + timedelta(days=4),
                            payment_id="pay_003",
                            payment_status="completed"
                        )
                    ]
                    
                    for subscription in sample_subscriptions:
                        session.add(subscription)
                    session.commit()
                    logger.info("Sample subscriptions created successfully")
                else:
                    logger.warning("Insufficient users or plans to create sample subscriptions")
                    
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating sample data: {str(e)}")
            raise
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def reset_and_init_database():
    """Reset database and initialize with fresh sample data"""
    try:
        # Drop all tables and recreate them
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables reset and recreated successfully")
        
        # Now initialize with sample data
        session = SessionLocal()
        try:
            # Create subscription plans with 100 ETB pricing
            plans = [
                SubscriptionPlan(
                    name="Basic Monthly",
                    description="Access to basic content for 1 month",
                    price_monthly=100.0,
                    price_yearly=1000.0,
                    duration_days=30,
                    is_active=True
                ),
                SubscriptionPlan(
                    name="Premium Monthly",
                    description="Access to all premium content for 1 month",
                    price_monthly=200.0,
                    price_yearly=2000.0,
                    duration_days=30,
                    is_active=True
                ),
                SubscriptionPlan(
                    name="Basic Yearly",
                    description="Access to basic content for 1 year (2 months free!)",
                    price_monthly=100.0,
                    price_yearly=1000.0,
                    duration_days=365,
                    is_active=True
                ),
                SubscriptionPlan(
                    name="Premium Yearly",
                    description="Access to all premium content for 1 year (4 months free!)",
                    price_monthly=200.0,
                    price_yearly=1600.0,
                    duration_days=365,
                    is_active=True
                ),
                SubscriptionPlan(
                    name="Weekly Trial",
                    description="7-day trial access to all content",
                    price_monthly=50.0,
                    price_yearly=500.0,
                    duration_days=7,
                    is_active=True
                )
            ]
            
            for plan in plans:
                session.add(plan)
            session.commit()
            logger.info("Subscription plans created successfully")
            
            # Create sample users
            sample_users = [
                User(
                    telegram_id=123456789,
                    username="john_doe",
                    first_name="John",
                    last_name="Doe",
                    email="john@example.com",
                    is_admin=True,
                    registration_date=datetime.utcnow() - timedelta(days=30)
                ),
                User(
                    telegram_id=987654321,
                    username="jane_smith",
                    first_name="Jane",
                    last_name="Smith",
                    email="jane@example.com",
                    registration_date=datetime.utcnow() - timedelta(days=15)
                ),
                User(
                    telegram_id=555666777,
                    username="alex_wilson",
                    first_name="Alex",
                    last_name="Wilson",
                    registration_date=datetime.utcnow() - timedelta(days=5)
                ),
                User(
                    telegram_id=111222333,
                    username="sarah_johnson",
                    first_name="Sarah",
                    last_name="Johnson",
                    email="sarah@example.com",
                    registration_date=datetime.utcnow() - timedelta(days=2)
                )
            ]
            
            for user in sample_users:
                session.add(user)
            session.commit()
            logger.info("Sample users created successfully")
            
            # Create sample content
            sample_content = [
                # Video Content
                Content(
                    title="Introduction to Python Programming",
                    description="Complete beginner's guide to Python programming with practical examples",
                    content_type="video",
                    file_path="/content/videos/python_intro.mp4",
                    file_size=1024000000,  # 1GB
                    duration=3600.0,  # 1 hour
                    thumbnail_path="/content/thumbnails/python_intro.jpg",
                    encryption_key_id="key_001",
                    created_date=datetime.utcnow() - timedelta(days=20)
                ),
                Content(
                    title="Advanced Web Development",
                    description="Master modern web development with React, Node.js, and databases",
                    content_type="video",
                    file_path="/content/videos/web_dev_advanced.mp4",
                    file_size=2048000000,  # 2GB
                    duration=7200.0,  # 2 hours
                    thumbnail_path="/content/thumbnails/web_dev.jpg",
                    encryption_key_id="key_002",
                    created_date=datetime.utcnow() - timedelta(days=15)
                ),
                Content(
                    title="Data Science Fundamentals",
                    description="Learn data analysis, visualization, and machine learning basics",
                    content_type="video",
                    file_path="/content/videos/data_science.mp4",
                    file_size=1536000000,  # 1.5GB
                    duration=5400.0,  # 1.5 hours
                    thumbnail_path="/content/thumbnails/data_science.jpg",
                    encryption_key_id="key_003",
                    created_date=datetime.utcnow() - timedelta(days=10)
                ),
                
                # PDF/Book Content
                Content(
                    title="Clean Code: A Handbook of Agile Software Craftsmanship",
                    description="Essential guide to writing clean, maintainable code",
                    content_type="pdf",
                    file_path="/content/books/clean_code.pdf",
                    file_size=15000000,  # 15MB
                    thumbnail_path="/content/thumbnails/clean_code.jpg",
                    encryption_key_id="key_004",
                    created_date=datetime.utcnow() - timedelta(days=25)
                ),
                Content(
                    title="Design Patterns: Elements of Reusable Object-Oriented Software",
                    description="The classic book on software design patterns",
                    content_type="pdf",
                    file_path="/content/books/design_patterns.pdf",
                    file_size=20000000,  # 20MB
                    thumbnail_path="/content/thumbnails/design_patterns.jpg",
                    encryption_key_id="key_005",
                    created_date=datetime.utcnow() - timedelta(days=18)
                ),
                Content(
                    title="The Pragmatic Programmer",
                    description="Your journey to mastery in software development",
                    content_type="pdf",
                    file_path="/content/books/pragmatic_programmer.pdf",
                    file_size=12000000,  # 12MB
                    thumbnail_path="/content/thumbnails/pragmatic_programmer.jpg",
                    encryption_key_id="key_006",
                    created_date=datetime.utcnow() - timedelta(days=12)
                ),
                
                # Audio Content
                Content(
                    title="Tech Podcast: Future of AI",
                    description="Discussion on artificial intelligence trends and future developments",
                    content_type="audio",
                    file_path="/content/audio/ai_podcast.mp3",
                    file_size=50000000,  # 50MB
                    duration=2700.0,  # 45 minutes
                    thumbnail_path="/content/thumbnails/ai_podcast.jpg",
                    encryption_key_id="key_007",
                    created_date=datetime.utcnow() - timedelta(days=7)
                ),
                Content(
                    title="Startup Success Stories",
                    description="Interviews with successful entrepreneurs and their journey",
                    content_type="audio",
                    file_path="/content/audio/startup_stories.mp3",
                    file_size=75000000,  # 75MB
                    duration=4500.0,  # 75 minutes
                    thumbnail_path="/content/thumbnails/startup_stories.jpg",
                    encryption_key_id="key_008",
                    created_date=datetime.utcnow() - timedelta(days=3)
                )
            ]
            
            for content in sample_content:
                session.add(content)
            session.commit()
            logger.info("Sample content created successfully")
            
            # Create sample subscriptions
            plans = session.query(SubscriptionPlan).all()
            users = session.query(User).all()
            
            sample_subscriptions = [
                Subscription(
                    user_id=users[0].id,  # John Doe - Admin
                    plan_id=plans[1].id,  # Premium Monthly
                    start_date=datetime.utcnow() - timedelta(days=15),
                    end_date=datetime.utcnow() + timedelta(days=15),
                    payment_id="pay_001",
                    payment_status="completed"
                ),
                Subscription(
                    user_id=users[1].id,  # Jane Smith
                    plan_id=plans[0].id,  # Basic Monthly
                    start_date=datetime.utcnow() - timedelta(days=10),
                    end_date=datetime.utcnow() + timedelta(days=20),
                    payment_id="pay_002",
                    payment_status="completed"
                ),
                Subscription(
                    user_id=users[2].id,  # Alex Wilson
                    plan_id=plans[4].id,  # Weekly Trial
                    start_date=datetime.utcnow() - timedelta(days=3),
                    end_date=datetime.utcnow() + timedelta(days=4),
                    payment_id="pay_003",
                    payment_status="completed"
                )
            ]
            
            for subscription in sample_subscriptions:
                session.add(subscription)
            session.commit()
            logger.info("Sample subscriptions created successfully")
            
            logger.info("Database reset and initialized with complete sample data")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating sample data: {str(e)}")
            raise
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        raise

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
