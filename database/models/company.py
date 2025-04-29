from sqlalchemy import Column, DateTime, Integer, String, Boolean
from database.database import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey

class Company(Base):
    __tablename__= "companies"
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False, unique=True, index=True)
    city = Column(String)
    state = Column(String)
    country = Column(String)
    industry = Column(String)
    company_size = Column(Integer)
    subscription_tier  = Column(String)
    is_active = Column(Boolean)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    is_verified = Column(Boolean, default=True)  
    deleted_at = Column(DateTime, nullable=True)
    users = relationship("User", back_populates="company")