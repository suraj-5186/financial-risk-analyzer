from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ChatMessageBase(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatHistoryResponse(BaseModel):
    id: str
    user_id: str
    session_id: Optional[str] = None
    sender: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True
