from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from database.database import Base


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    refresh_jti_hash = Column(String, nullable=False, unique=True, index=True)
    session_binding_hash = Column(String, nullable=True)
    device_info = Column(String, nullable=True)
    issued_ip_address = Column(String, nullable=True)
    last_seen_ip_address = Column(String, nullable=True)
    revoked = Column(Boolean, default=False, nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
