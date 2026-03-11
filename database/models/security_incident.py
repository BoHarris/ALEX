from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from database.database import Base


class SecurityIncident(Base):
    __tablename__ = "security_incidents"

    id = Column(Integer, primary_key=True, index=True)
    severity = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True, default="open")
    description = Column(Text, nullable=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
