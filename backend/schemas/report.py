from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ReportBase(BaseModel):
    report_type: str = "Monthly"
    file_path: str
    month: str
    summary: Optional[str] = None

class ReportCreate(ReportBase):
    pass

class ReportResponse(ReportBase):
    id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True
