import datetime
import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    risk_level = Column(String, nullable=False) # "Low", "Medium", "High"
    health_score = Column(Float, nullable=False)
    income = Column(Float, nullable=False)
    expenses = Column(Float, nullable=False)
    savings = Column(Float, nullable=False)
    debt = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
