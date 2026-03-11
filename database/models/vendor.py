from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    compliance_record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=False, unique=True, index=True)
    vendor_name = Column(String, nullable=False, index=True)
    service_category = Column(String, nullable=False)
    data_access_level = Column(String, nullable=False)
    contract_start_date = Column(DateTime(timezone=True), nullable=True)
    contract_end_date = Column(DateTime(timezone=True), nullable=True)
    risk_rating = Column(String, nullable=True, index=True)
    security_review_status = Column(String, nullable=False, default="pending", index=True)
    last_review_date = Column(DateTime(timezone=True), nullable=True)
    document_links = Column(Text, nullable=True)
