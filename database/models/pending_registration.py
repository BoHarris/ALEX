from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from database.database import Base


class PendingRegistration(Base):
    __tablename__ = "pending_registrations"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    company_name = Column(String, nullable=True)
    create_company = Column(Boolean, default=False, nullable=False)
    role = Column(String, nullable=False)
    company_id = Column(Integer, nullable=True, index=True)
    webauthn_user_handle = Column(String, nullable=False, unique=True, index=True)
    challenge = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
