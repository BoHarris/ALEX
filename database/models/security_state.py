from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from database.database import Base


class SecurityState(Base):
    __tablename__ = "security_states"
    __table_args__ = (
        UniqueConstraint("namespace", "state_key", name="uq_security_states_namespace_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    namespace = Column(String, nullable=False, index=True)
    state_key = Column(String, nullable=False, index=True)
    counter_value = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
