from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from database.database import Base


class ComplianceAttachment(Base):
    __tablename__ = "compliance_attachments"

    id = Column(Integer, primary_key=True, index=True)
    compliance_record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    label = Column(String, nullable=False)
    attachment_type = Column(String, nullable=False, default="link")
    path_or_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
