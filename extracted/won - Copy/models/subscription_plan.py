# Subscription plan model representing subscription plans
# Fields: name, description, price_monthly, price_yearly, duration_days, etc.

from sqlalchemy import Column, Integer, String, Float, Boolean
from models.base import Base

class SubscriptionPlan(Base):
    __tablename__ = 'subscription_plans'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    price_monthly = Column(Float, nullable=False)
    price_yearly = Column(Float, nullable=False)
    duration_days = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)