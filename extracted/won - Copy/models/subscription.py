# Subscription model representing user subscriptions
# Fields: user_id, plan_id, start_date, end_date, payment_id, etc.

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime

class Subscription(Base):
    __tablename__ = 'user_subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    plan_id = Column(Integer, ForeignKey('subscription_plans.id'), nullable=False)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    payment_id = Column(String)  # Telegram payment ID or Chapa transaction ID
    payment_status = Column(String)  # pending, completed, failed, refunded
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan")