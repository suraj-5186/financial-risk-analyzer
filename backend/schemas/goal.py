from pydantic import BaseModel
from datetime import date
from typing import Optional

class FinancialGoalBase(BaseModel):
    title: str
    target_amount: float
    target_date: date

class FinancialGoalCreate(FinancialGoalBase):
    pass

class FinancialGoalUpdate(BaseModel):
    title: Optional[str] = None
    target_amount: Optional[float] = None
    current_amount: Optional[float] = None
    target_date: Optional[date] = None

class FinancialGoalResponse(FinancialGoalBase):
    id: int
    current_amount: float
    user_id: str

    class Config:
        from_attributes = True
