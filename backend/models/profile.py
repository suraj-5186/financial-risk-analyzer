from sqlalchemy import Column, Integer, Float, ForeignKey, String
from sqlalchemy.orm import relationship
from models.base import Base

class FinancialProfile(Base):
    __tablename__ = "financial_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    monthly_income = Column(Float, default=50000.0)
    savings_rate = Column(Float, default=20.0)
    debt_ratio = Column(Float, default=30.0)
    spending_consistency = Column(Float, default=70.0)
    emergency_fund_months = Column(Integer, default=3)
    health_score = Column(Integer, default=65)
    monthly_budget = Column(Float, default=50000.0)
    savings_goal_title = Column(String, default="Emergency Fund")
    savings_goal_target = Column(Float, default=100000.0)
    savings_goal_current = Column(Float, default=30000.0)

    user = relationship("User", back_populates="profile")
