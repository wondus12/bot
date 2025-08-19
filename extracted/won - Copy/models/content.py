# Content model for tracking protected files
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime

class Content(Base):
    __tablename__ = 'contents'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    content_type = Column(String, nullable=False)  # 'video', 'pdf', 'audio'
    file_path = Column(String, nullable=False)  # Encrypted file path
    file_size = Column(Integer)  # File size in bytes
    duration = Column(Float)  # For videos/audio (in seconds)
    thumbnail_path = Column(String)  # Preview image path
    encryption_key_id = Column(String, nullable=False)  # Key identifier
    is_active = Column(Boolean, default=True)
    created_date = Column(DateTime, default=datetime.utcnow)
    
    # Access tracking
    content_accesses = relationship("ContentAccess", back_populates="content")
    
    def __repr__(self):
        return f"<Content {self.title} ({self.content_type})>"

class ContentAccess(Base):
    __tablename__ = 'content_accesses'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content_id = Column(Integer, ForeignKey('contents.id'), nullable=False)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    access_type = Column(String, nullable=False)  # 'download', 'stream', 'view'
    access_date = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
    user_agent = Column(String)
    
    # Relationships
    user = relationship("User")
    content = relationship("Content", back_populates="content_accesses")
    device = relationship("Device", back_populates="content_accesses")
    
    def __repr__(self):
        return f"<ContentAccess {self.content.title} on {self.device.device_name}>"
