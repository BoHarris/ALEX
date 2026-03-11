from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from database.database import Base


class ComplianceTestFailureTask(Base):
    __tablename__ = "compliance_test_failure_tasks"

    id = Column(Integer, primary_key=True, index=True)
    compliance_record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=False, unique=True, index=True)
    organization_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    test_node_id = Column(String, nullable=False, index=True)
    latest_failed_run_id = Column(Integer, ForeignKey("compliance_test_runs.id"), nullable=False, index=True)
    latest_failed_result_id = Column(Integer, ForeignKey("compliance_test_case_results.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="open", index=True)
    priority = Column(String, nullable=False, default="medium", index=True)
    assignee_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    failure_signature = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
