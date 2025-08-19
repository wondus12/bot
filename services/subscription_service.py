# Subscription business logic
# Plan management, subscription creation, payment processing, etc.

from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from models.subscription import Subscription
from models.user import User
from models.subscription_plan import SubscriptionPlan
import logging

logger = logging.getLogger(__name__)

class SubscriptionService:
    @staticmethod
    async def get_active_subscription(telegram_id, session):
        """Get user's active subscription"""
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return None
        
        return session.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.is_active == True,
            Subscription.end_date > datetime.utcnow()
        ).first()
    
    @staticmethod
    async def get_subscription_plans(session):
        """Get all active subscription plans"""
        return session.query(SubscriptionPlan).filter(
            SubscriptionPlan.is_active == True
        ).all()
    
    @staticmethod
    async def create_subscription(telegram_id, plan_id, payment_id, session):
        """Create a new subscription"""
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
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
    async def cancel_subscription(subscription_id, session):
        """Cancel a subscription"""
        subscription = session.query(Subscription).get(subscription_id)
        if subscription:
            subscription.is_active = False
            session.commit()
            return True
        return False