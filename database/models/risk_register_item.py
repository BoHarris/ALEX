from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database.database import Base


class RiskRegisterItem(Base):
    __tablename__ = "risk_register_items"

    id = Column(Integer, primary_key=True, index=True)
    compliance_record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=False, unique=True, index=True)
    risk_title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    risk_category = Column(String, nullable=False, index=True)
    likelihood = Column(Integer, nullable=False)
    impact = Column(Integer, nullable=False)
    risk_score = Column(Integer, nullable=False, index=True)
    mitigation_plan = Column(Text, nullable=True)
    owner_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    review_date = Column(DateTime(timezone=True), nullable=True)
