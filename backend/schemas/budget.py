from pydantic import BaseModel, Field, field_validator
from typing import Optional

class BudgetBase(BaseModel):
    category: str = Field(..., min_length=1, max_length=50)
    monthly_limit: float = Field(..., ge=0, description="Monthly budget limit must be greater than or equal to 0")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Category name cannot be blank")
        return cleaned

class BudgetCreate(BudgetBase):
    pass

class BudgetUpdate(BaseModel):
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    monthly_limit: Optional[float] = Field(None, ge=0)
    spent: Optional[float] = Field(None, ge=0)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Category name cannot be blank")
            return cleaned
        return v

class BudgetResponse(BudgetBase):
    id: int
    spent: float
    user_id: str
    remaining: Optional[float] = None
    utilization_pct: Optional[float] = None

    class Config:
        from_attributes = True
