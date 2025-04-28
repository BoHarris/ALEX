from sqlalchemy import Column, Integer, String, Boolean
from database.database import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    first_namename = Column(String)
    last_namename = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True) #TODO: make it not nullable
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(String, default=func.now())
    tier = Column(String, default="free")
    is_verified = Column(Boolean, default=False)
    device_tokens = relationship("DeviceToken", back_populates="user")
    email_verification_token = Column(String, nullable=True)