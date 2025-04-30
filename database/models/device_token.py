from sqlalchemy import (
    Column, 
    Integer, 
    String, 
    ForeignKey, 
    DateTime,
    UniqueConstraint,)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.database import Base
import secrets

class DeviceToken(Base):
    __tablename__ = 'device_tokens'
    __table_args__ = (
  UniqueConstraint("user_id", "device_fingerprint", name="uq_user_device"),
)
    
    id = Column(Integer, primary_key=True, index =True)
    user_id = Column(Integer, ForeignKey('users.id'))
    token = Column(String, unique=True, default=lambda: secrets.token_hex(32))
    device_fingerprint = Column(String, nullable=False) 
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    last_used_at = Column(DateTime, default=datetime.now(timezone.utc))
    user = relationship("User", back_populates="device_tokens")