from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from database.database import Base


class LLMSettings(Base):
    __tablename__ = "llm_settings"

    id = Column(Integer, primary_key=True, default=1)
    enabled = Column(Boolean, nullable=False, default=False)
    model = Column(String, nullable=False, default="claude-3-5-sonnet-20241022")
    max_tokens = Column(Integer, nullable=False, default=1024)
    temperature = Column(Float, nullable=False, default=0.7)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)