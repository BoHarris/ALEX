from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from database.database import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class ScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    risk_score = Column(Integer, nullable=False)
    pii_types_found = Column(String, nullable=True)
    redacted_type_counts = Column(String, nullable=True)
    total_pii_found = Column(Integer, nullable=False)
    redacted_file_path = Column(String, nullable=True)
    report_html_path = Column(String, nullable=True)
    report_pdf_path = Column(String, nullable=True)
    scanned_at = Column(DateTime, server_default=func.now(), nullable=False)
    status = Column(String, nullable=False, default="active", index=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    retention_expiration = Column(DateTime(timezone=True), nullable=True, index=True)
    
    user = relationship("User")
    company = relationship("Company")
    
    

