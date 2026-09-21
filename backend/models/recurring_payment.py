import datetime
import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Date, Integer, Text
from sqlalchemy.orm import relationship
from models.base import Base

class RecurringPayment(Base):
    __tablename__ = "recurring_payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    merchant_name = Column(String, nullable=False)
    normalized_name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, default="Other")
    frequency = Column(String, nullable=False) # "weekly", "biweekly", "monthly", "quarterly", "annual"
    average_amount = Column(Float, nullable=False)
    last_amount = Column(Float, nullable=False)
    estimated_monthly_cost = Column(Float, nullable=False)
    estimated_annual_cost = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False, default=0.7)
    status = Column(String, nullable=False, default="detected") # "detected", "confirmed", "dismissed"
    last_payment_date = Column(Date, nullable=False)
    next_estimated_date = Column(Date, nullable=True)
    transaction_count = Column(Integer, nullable=False, default=2)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="recurring_payments")
