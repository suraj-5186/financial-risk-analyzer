from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class NotificationBase(BaseModel):
    title: str
    message: str
    type: str
    is_read: bool = False

class NotificationResponse(NotificationBase):
    id: int
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True
