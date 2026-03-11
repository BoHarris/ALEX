from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from database.database import Base


class ComplianceApproval(Base):
    __tablename__ = "compliance_approvals"

    id = Column(Integer, primary_key=True, index=True)
    compliance_record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=False, index=True)
    approver_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="pending", index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=True)
