from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database.database import Base


class GRCIncident(Base):
    __tablename__ = "grc_incidents"

    id = Column(Integer, primary_key=True, index=True)
    compliance_record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=False, unique=True, index=True)
    severity = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    detected_by_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    detected_at = Column(DateTime(timezone=True), nullable=False)
    assigned_to_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    resolution_notes = Column(Text, nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    root_cause = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)
