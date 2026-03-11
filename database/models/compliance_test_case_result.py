from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from database.database import Base


class ComplianceTestCaseResult(Base):
    __tablename__ = "compliance_test_case_results"

    id = Column(Integer, primary_key=True, index=True)
    test_run_id = Column(Integer, ForeignKey("compliance_test_runs.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    file_name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, index=True)
    duration_ms = Column(Integer, nullable=True)
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    last_run_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
