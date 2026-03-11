from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database.database import Base


class CodeReview(Base):
    __tablename__ = "code_reviews"

    id = Column(Integer, primary_key=True, index=True)
    compliance_record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=False, unique=True, index=True)
    summary = Column(Text, nullable=False)
    review_type = Column(String, nullable=False, default="internal_change", index=True)
    risk_level = Column(String, nullable=False, default="medium", index=True)
    created_by_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    assigned_reviewer_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    target_release = Column(String, nullable=True, index=True)
    prompt_text = Column(Text, nullable=True)
    design_notes = Column(Text, nullable=True)
    code_notes = Column(Text, nullable=True)
    files_impacted = Column(Text, nullable=True)
    testing_notes = Column(Text, nullable=True)
    security_review_notes = Column(Text, nullable=True)
    privacy_review_notes = Column(Text, nullable=True)
    reviewer_decision = Column(String, nullable=True, index=True)
    reviewer_comments = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
