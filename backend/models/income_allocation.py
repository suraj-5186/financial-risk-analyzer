import datetime
from sqlalchemy import Column, Integer, Float, ForeignKey, String, DateTime
from sqlalchemy.orm import relationship
from models.base import Base

class IncomeAllocation(Base):
    __tablename__ = "income_allocations"

    id = Column(Integer, primary_key=True, index=True)
    income_source_id = Column(Integer, ForeignKey("income_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = Column(Integer, ForeignKey("financial_goals.id", ondelete="SET NULL"), nullable=True, index=True)
    allocation_type = Column(String, nullable=False)  # "GOAL" or "FREE_CASH"
    amount = Column(Float, nullable=False)
    notes = Column(String, nullable=True)
    allocated_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    income_source = relationship("IncomeSource", back_populates="allocations")
    goal = relationship("FinancialGoal", back_populates="income_allocations")
    user = relationship("User")
