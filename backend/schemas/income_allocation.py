import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

class GoalAllocationItem(BaseModel):
    goal_id: int
    amount: float = Field(..., gt=0, description="Amount to allocate to this goal")
    notes: Optional[str] = None

class IncomeAllocationRequest(BaseModel):
    allocations: List[GoalAllocationItem] = Field(default_factory=list)
    free_cash_amount: float = Field(0.0, ge=0, description="Amount left as uncommitted free cash")

class IncomeAllocationItemResponse(BaseModel):
    id: int
    income_source_id: int
    goal_id: Optional[int] = None
    goal_title: Optional[str] = None
    allocation_type: str  # "GOAL" or "FREE_CASH"
    amount: float
    notes: Optional[str] = None
    allocated_at: datetime.datetime

    class Config:
        from_attributes = True

class UpdatedGoalSummary(BaseModel):
    id: int
    title: Optional[str] = None
    new_current_amount: float
    target_amount: float
    status: str

class IncomeAllocationResponse(BaseModel):
    status: str
    income_source_id: int
    total_amount: float
    allocated_to_goals: float
    free_cash: float
    unallocated_amount: float = 0.0
    allocations: List[IncomeAllocationItemResponse]
    updated_goals: List[dict]
