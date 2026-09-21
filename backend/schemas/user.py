from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class UserBase(BaseModel):
    full_name: str
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

from typing import Optional

class UserResponse(UserBase):
    id: str
    created_at: datetime
    profile_photo_url: Optional[str] = None
    is_admin: bool
    currency: str
    theme: str
    notify_budget_exceeded: bool
    notify_savings_low: bool
    notify_high_risk: bool
    notify_anomalies: bool

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    currency: Optional[str] = None
    theme: Optional[str] = None
    notify_budget_exceeded: Optional[bool] = None
    notify_savings_low: Optional[bool] = None
    notify_high_risk: Optional[bool] = None
    notify_anomalies: Optional[bool] = None
    monthly_income: Optional[float] = None
    monthly_budget: Optional[float] = None
    savings_goal_title: Optional[str] = None
    savings_goal_target: Optional[float] = None
    savings_goal_current: Optional[float] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, description="URL-safe reset token")
    new_password: str = Field(..., min_length=6, max_length=128, description="New user password")

class GenericMessageResponse(BaseModel):
    status: str = "success"
    message: str
