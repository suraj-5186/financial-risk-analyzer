from pydantic import BaseModel
from datetime import datetime

class UserSettingsBase(BaseModel):
    monthly_budget: float = 50000.0
    savings_goal: float = 100000.0
    currency: str = "INR"
    theme: str = "dark"
    notify_budget_exceeded: bool = True
    notify_savings_low: bool = True
    notify_high_risk: bool = True
    notify_anomalies: bool = True

class UserSettingsUpdate(UserSettingsBase):
    pass

class UserSettingsResponse(UserSettingsBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
