import datetime
from sqlalchemy import Column, Integer, Float, ForeignKey, String, Boolean, Date, DateTime
from sqlalchemy.orm import relationship
from models.base import Base

class IncomeSource(Base):
    __tablename__ = "income_sources"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)          # e.g. "Salary", "Freelance", "Stipend", "Annual Bonus"
    amount = Column(Float, nullable=False)         # Amount per frequency period or one-time total
    income_type = Column(String, default="recurring", nullable=False)  # "recurring" | "one_time"
    frequency = Column(String, default="monthly", nullable=False)      # "monthly", "weekly", "one_time"
    is_recurring = Column(Boolean, default=True, nullable=False)
    next_expected_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="income_sources")
    allocations = relationship("IncomeAllocation", back_populates="income_source", cascade="all, delete-orphan")
