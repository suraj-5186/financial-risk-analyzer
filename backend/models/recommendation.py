import datetime
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import Base

class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_recommendations_user_id_id"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False) # e.g. "Savings", "Budget", "Debt", "Investment"
    priority = Column(String, nullable=False) # "High", "Medium", "Low"
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    is_applied = Column(Boolean, default=False)
    action_type = Column(String, nullable=True) # e.g. "ALLOCATION", "BUDGET_ADJUST", "GOAL_TOPUP"
    action_payload = Column(String, nullable=True) # JSON payload for the action
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    applied_at = Column(DateTime, nullable=True)

    user = relationship("User")
