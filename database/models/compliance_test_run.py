from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from database.database import Base


class ComplianceTestRun(Base):
    __tablename__ = "compliance_test_runs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    suite_name = Column(String, nullable=False)
    status = Column(String, nullable=False, index=True)
    coverage_percent = Column(Numeric(5, 2), nullable=True)
    report_link = Column(Text, nullable=True)
    run_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
