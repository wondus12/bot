# Base model class with common attributes and methods
# All other models will inherit from this class

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()