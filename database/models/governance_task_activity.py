from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from database.database import Base


class GovernanceTaskActivity(Base):
    __tablename__ = "governance_task_activities"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("governance_tasks.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    actor_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    actor_type = Column(String, nullable=True, index=True)
    actor_label = Column(String, nullable=True)
    action = Column(String, nullable=False, index=True)
    from_value = Column(String, nullable=True)
    to_value = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
