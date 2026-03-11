from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from database.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    event_category = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=True, index=True)
    resource_id = Column(String, nullable=True, index=True)
    ip_address = Column(String, nullable=True)
    device_fingerprint = Column(String, nullable=True)
    event_metadata = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
