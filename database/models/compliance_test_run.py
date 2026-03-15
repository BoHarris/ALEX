from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from database.database import Base


class ComplianceTestRun(Base):
    __tablename__ = "compliance_test_runs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    triggered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    triggered_by_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    run_type = Column(String, nullable=False, default="recorded", index=True)
    trigger_source = Column(String, nullable=False, default="manual", index=True)
    execution_engine = Column(String, nullable=True)
    pytest_node_id = Column(Text, nullable=True, index=True)
    category = Column(String, nullable=False, index=True)
    suite_name = Column(String, nullable=False)
    dataset_name = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, index=True)
    total_tests = Column(Integer, nullable=False, default=0)
    passed_tests = Column(Integer, nullable=False, default=0)
    failed_tests = Column(Integer, nullable=False, default=0)
    skipped_tests = Column(Integer, nullable=False, default=0)
    accuracy_score = Column(Numeric(6, 4), nullable=True)
    coverage_percent = Column(Numeric(5, 2), nullable=True)
    report_link = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    return_code = Column(Integer, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    failure_summary = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    run_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
