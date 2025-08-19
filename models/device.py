# Device model for tracking registered devices
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime
import json

class Device(Base):
    __tablename__ = 'devices'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    device_id = Column(String, nullable=False)  # Unique device identifier
    device_type = Column(String, nullable=False)  # 'mobile' or 'laptop'
    platform = Column(String, nullable=False)  # 'android', 'ios', 'windows', 'macos'
    device_name = Column(String)  # User-friendly name
    fingerprint = Column(Text)  # JSON string of device characteristics
    public_key = Column(Text)  # Device's public key for encryption
    is_active = Column(Boolean, default=True)
    registered_date = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="devices")
    content_accesses = relationship("ContentAccess", back_populates="device")
    
    def set_fingerprint(self, fingerprint_data):
        """Store device fingerprint as JSON"""
        self.fingerprint = json.dumps(fingerprint_data)
    
    def get_fingerprint(self):
        """Get device fingerprint as dict"""
        return json.loads(self.fingerprint) if self.fingerprint else {}
    
    def __repr__(self):
        return f"<Device {self.device_name} ({self.platform})>"
