from sqlalchemy import Column, ForeignKey, Integer, String, Text

from database.database import Base


class WikiPage(Base):
    __tablename__ = "wiki_pages"

    id = Column(Integer, primary_key=True, index=True)
    compliance_record_id = Column(Integer, ForeignKey("compliance_records.id"), nullable=False, unique=True, index=True)
    parent_page_id = Column(Integer, ForeignKey("wiki_pages.id"), nullable=True, index=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    category = Column(String, nullable=False, index=True)
    template_name = Column(String, nullable=True)
    tags = Column(Text, nullable=True)
    content_markdown = Column(Text, nullable=False, default="")
    version = Column(Integer, nullable=False, default=1)
