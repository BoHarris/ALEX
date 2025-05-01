from sqlalchemy import Column, DateTime, Integer, String, Boolean
from database.database import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from database.models.company import Company

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True) #TODO: make it not nullable
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    tier = Column(String, default="free")
    is_verified = Column(Boolean, default=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    phone_number = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    locale = Column(String, nullable=True)
    profile_pic = Column(String, nullable=True)
    
    #device token relationship
    device_tokens = relationship("DeviceToken", back_populates="user")
    
    #email verification token 
    email_verification_token = Column(String, nullable=True)
        
    #Relationship to company
    company_id = Column(Integer, ForeignKey("companies.id"), nullable= True)
    company = relationship(Company, back_populates="users")