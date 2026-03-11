from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String

from database.database import Base


class TrainingAssignment(Base):
    __tablename__ = "training_assignments"

    id = Column(Integer, primary_key=True, index=True)
    compliance_record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=False, unique=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    training_module_id = Column(Integer, ForeignKey("training_modules.id"), nullable=False, index=True)
    completion_status = Column(String, nullable=False, default="assigned", index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    quiz_score = Column(Numeric(5, 2), nullable=True)
