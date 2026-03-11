from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database.database import Base


class AccessReview(Base):
    __tablename__ = "access_reviews"

    id = Column(Integer, primary_key=True, index=True)
    compliance_record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=False, unique=True, index=True)
    reviewer_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    reviewed_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    decision = Column(String, nullable=False, default="pending", index=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    permissions_snapshot = Column(Text, nullable=True)
    last_access_review_date = Column(DateTime(timezone=True), nullable=True)
