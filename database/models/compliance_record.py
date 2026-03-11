from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from database.database import Base


class ComplianceRecord(Base):
    __tablename__ = "compliance_records"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    module = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft", index=True)
    owner_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    review_date = Column(DateTime(timezone=True), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_by_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    updated_by_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
