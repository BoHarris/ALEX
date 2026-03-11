from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from database.database import Base


class CompanySettings(Base):
    __tablename__ = "company_settings"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, unique=True, index=True)
    default_policy_label = Column(String, nullable=True)
    default_report_display_name = Column(String, nullable=True)
    allowed_upload_types = Column(Text, nullable=True)
    contact_email = Column(String, nullable=True)
    compliance_mode = Column(String, nullable=True)
    branding_primary_color = Column(String, nullable=True)
    retention_days_display = Column(Integer, nullable=True)
    retention_days = Column(Integer, nullable=True)
    require_storage_encryption = Column(String, nullable=True)
    secure_cookie_enforced = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
