from pydantic import BaseModel
from datetime import datetime

class RecommendationBase(BaseModel):
    title: str
    description: str
    category: str
    priority: str
    is_read: bool = False

class RecommendationCreate(RecommendationBase):
    pass

class RecommendationResponse(RecommendationBase):
    id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True
