import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    report_type = Column(String, nullable=False, default="Monthly")
    file_path = Column(String, nullable=False)
    month = Column(String, nullable=False) # e.g. "2026-06"
    summary = Column(String, nullable=True) # AI-generated or system summary text
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
