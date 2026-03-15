from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from database.database import Base


class GovernanceTask(Base):
    __tablename__ = "governance_tasks"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="todo", index=True)
    priority = Column(String, nullable=False, default="medium", index=True)
    source_type = Column(String, nullable=False, default="manual", index=True)
    source_id = Column(String, nullable=True, index=True)
    source_module = Column(String, nullable=False, default="manual", index=True)
    incident_id = Column(Integer, ForeignKey("grc_incidents.id"), nullable=True, index=True)
    assignee_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    assignee_type = Column(String, nullable=True, index=True)
    assignee_label = Column(String, nullable=True)
    reporter_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True, index=True)
    linked_source = Column(String, nullable=True, index=True)  # For linking to specific source records
    linked_source_type = Column(String, nullable=True, index=True)  # Type of the linked source
    linked_source_id = Column(Integer, nullable=True, index=True)  # ID of the linked source
    linked_source_metadata = Column(Text, nullable=True)  # Metadata for the linked source
