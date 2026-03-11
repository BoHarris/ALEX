from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from database.database import Base


class ComplianceActivity(Base):
    __tablename__ = "compliance_activities"

    id = Column(Integer, primary_key=True, index=True)
    compliance_record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
