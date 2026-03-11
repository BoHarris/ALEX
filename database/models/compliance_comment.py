from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.sql import func

from database.database import Base


class ComplianceComment(Base):
    __tablename__ = "compliance_comments"

    id = Column(Integer, primary_key=True, index=True)
    compliance_record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
