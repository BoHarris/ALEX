from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, UniqueConstraint, Index
from sqlalchemy.sql import func

from database.database import Base


class ScanQuotaCounter(Base):
    __tablename__ = "scan_quota_counters"
    __table_args__ = (
        UniqueConstraint("user_id", "day", name="uq_scan_quota_user_day"),
        Index('idx_scan_quota_user_day', 'user_id', 'day'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day = Column(Date, nullable=False, index=True)
    count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
