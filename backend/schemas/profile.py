from pydantic import BaseModel
from typing import Optional

class FinancialProfileBase(BaseModel):
    monthly_income: float = 50000.0
    savings_rate: float = 20.0
    debt_ratio: float = 30.0
    spending_consistency: float = 70.0
    emergency_fund_months: int = 3
    monthly_budget: float = 50000.0
    savings_goal_title: str = "Emergency Fund"
    savings_goal_target: float = 100000.0
    savings_goal_current: float = 30000.0

class FinancialProfileResponse(FinancialProfileBase):
    id: int
    user_id: str
    health_score: int

    class Config:
        from_attributes = True

class FinancialProfileUpdate(BaseModel):
    monthly_income: Optional[float] = None
    savings_rate: Optional[float] = None
    debt_ratio: Optional[float] = None
    spending_consistency: Optional[float] = None
    emergency_fund_months: Optional[int] = None
    monthly_budget: Optional[float] = None
    savings_goal_title: Optional[str] = None
    savings_goal_target: Optional[float] = None
    savings_goal_current: Optional[float] = None
