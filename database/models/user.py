from sqlalchemy import Column, DateTime, Integer, String, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    
    email = Column(String, unique=True, index=True, nullable=False)
    
    hashed_password = Column(String, nullable=True)
    tier = Column(String, default="free", nullable=False)
    role = Column(String, default="member", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    phone_number = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    locale = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)
    refresh_version = Column(Integer, default=0, nullable=False)
    has_completed_onboarding = Column(Boolean, default=False, nullable=False)
    
    #Email verification token
    email_verification_token = Column(String, nullable=True)
    
    # Passkey / WebAuthn fields
    webauthn_credential_id = Column(String, nullable=True, unique=True,index=True)
    webauthn_public_key = Column(String, nullable=True)
    webauthn_sign_count = Column(Integer, default=0, nullable=False)
    webauthn_transports = Column(String, nullable=True)
    webauthn_user_handle = Column(String, nullable=True, unique=True,index=True)

    #Relationship to company
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    company = relationship("Company", back_populates="users")
    
