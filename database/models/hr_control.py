from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from database.database import Base


class HRControl(Base):
    __tablename__ = "hr_controls"

    id = Column(Integer, primary_key=True, index=True)
    compliance_record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=False, unique=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    control_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="pending", index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
