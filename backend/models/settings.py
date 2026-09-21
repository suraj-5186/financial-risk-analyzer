import datetime
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from models.base import Base

class UserSettings(Base):
    __tablename__ = "settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    monthly_budget = Column(Float, default=50000.0)
    savings_goal = Column(Float, default=100000.0)
    currency = Column(String, default="INR")
    theme = Column(String, default="dark")
    notify_budget_exceeded = Column(Boolean, default=True)
    notify_savings_low = Column(Boolean, default=True)
    notify_high_risk = Column(Boolean, default=True)
    notify_anomalies = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User")
