from pydantic import BaseModel
from datetime import datetime

class PredictionBase(BaseModel):
    risk_level: str
    health_score: float
    income: float
    expenses: float
    savings: float
    debt: float

class PredictionCreate(PredictionBase):
    pass

class PredictionResponse(PredictionBase):
    id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True
