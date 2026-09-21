from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional, List

class RecurringPaymentBase(BaseModel):
    merchant_name: str
    normalized_name: str
    category: str = "Other"
    frequency: str = Field(..., description="weekly, biweekly, monthly, quarterly, annual")
    average_amount: float = Field(..., gt=0)
    last_amount: float = Field(..., gt=0)
    estimated_monthly_cost: float
    estimated_annual_cost: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    status: str = Field(default="detected", description="detected, confirmed, dismissed")
    last_payment_date: date
    next_estimated_date: Optional[date] = None
    transaction_count: int = 2
    notes: Optional[str] = None

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v: str) -> str:
        valid_frequencies = ["weekly", "biweekly", "monthly", "quarterly", "annual"]
        if v.lower() not in valid_frequencies:
            raise ValueError(f"Frequency must be one of {valid_frequencies}")
        return v.lower()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = ["detected", "confirmed", "dismissed"]
        if v.lower() not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v.lower()

class RecurringPaymentResponse(RecurringPaymentBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class RecurringPaymentUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    frequency: Optional[str] = None
    average_amount: Optional[float] = None

    @field_validator("status")
    @classmethod
    def validate_status_opt(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_statuses = ["detected", "confirmed", "dismissed"]
            if v.lower() not in valid_statuses:
                raise ValueError(f"Status must be one of {valid_statuses}")
            return v.lower()
        return v

    @field_validator("frequency")
    @classmethod
    def validate_frequency_opt(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_frequencies = ["weekly", "biweekly", "monthly", "quarterly", "annual"]
            if v.lower() not in valid_frequencies:
                raise ValueError(f"Frequency must be one of {valid_frequencies}")
            return v.lower()
        return v

class RecurringPaymentSummaryResponse(BaseModel):
    total_monthly_commitment: float
    total_annual_commitment: float
    active_subscriptions_count: int
    confirmed_count: int
    detected_count: int
    dismissed_count: int
    upcoming_payments_next_30_days: List[RecurringPaymentResponse]

class ScanResponse(BaseModel):
    scanned_transactions_count: int
    new_detected_count: int
    updated_count: int
    total_active_count: int
    items: List[RecurringPaymentResponse]
    message: str
