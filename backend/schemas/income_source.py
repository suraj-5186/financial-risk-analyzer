from pydantic import BaseModel, Field
from typing import Optional, List
import datetime

class IncomeSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    amount: float = Field(..., gt=0)
    income_type: str = "recurring"  # "recurring" | "one_time"
    frequency: str = "monthly"       # "monthly" | "weekly" | "one_time"
    is_recurring: bool = True
    next_expected_date: Optional[datetime.date] = None
    is_active: bool = True

class IncomeSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    amount: float = Field(..., gt=0)
    income_type: str = "recurring"  # "recurring" | "one_time"
    frequency: str = "monthly"       # "monthly" | "weekly" | "one_time"
    is_recurring: Optional[bool] = None
    next_expected_date: Optional[datetime.date] = None
    is_active: bool = True

class IncomeSourceUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    income_type: Optional[str] = None
    frequency: Optional[str] = None
    is_recurring: Optional[bool] = None
    next_expected_date: Optional[datetime.date] = None
    is_active: Optional[bool] = None

class IncomeSourceResponse(IncomeSourceBase):
    id: int
    user_id: str
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    allocated_to_goals: float = 0.0
    free_cash: float = 0.0
    unallocated_amount: float = 0.0

    class Config:
        from_attributes = True
