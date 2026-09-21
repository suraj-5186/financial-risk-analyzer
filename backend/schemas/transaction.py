from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional, List, Any
from schemas.profile import FinancialProfileResponse
from schemas.budget import BudgetResponse
from schemas.goal import FinancialGoalResponse

class TransactionBase(BaseModel):
    type: str = Field(..., description="Must be 'Income' or 'Expense'")
    category: str
    amount: float = Field(..., gt=0, description="Amount must be greater than 0")
    description: Optional[str] = None
    transaction_date: date = Field(..., description="Date of the transaction")
    payment_method: str
    category_confidence: Optional[float] = 1.0
    auto_category: Optional[str] = None
    is_reviewed: Optional[bool] = True

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ["Income", "Expense"]:
            raise ValueError("Type must be either 'Income' or 'Expense'")
        return v

    @field_validator("transaction_date")
    @classmethod
    def validate_date(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Transaction date cannot be in the future")
        return v

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    type: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    transaction_date: Optional[date] = None
    payment_method: Optional[str] = None
    category_confidence: Optional[float] = None
    auto_category: Optional[str] = None
    is_reviewed: Optional[bool] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["Income", "Expense"]:
            raise ValueError("Type must be either 'Income' or 'Expense'")
        return v

    @field_validator("transaction_date")
    @classmethod
    def validate_date(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > date.today():
            raise ValueError("Transaction date cannot be in the future")
        return v

class TransactionResponse(TransactionBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Schemas for Auto-Categorization and Reviewable CSV Imports
class CategorizeRequest(BaseModel):
    description: str
    type: str = "Expense"
    amount: Optional[float] = 0.0

class CategorizeResponse(BaseModel):
    suggested_category: str
    confidence: float
    explanation: str
    is_reviewed: bool
    needs_review: bool = False

    def model_post_init(self, __context: Any) -> None:
        self.needs_review = (self.suggested_category == "Needs Review" or self.confidence < 0.70)

class ParseCsvItem(BaseModel):
    temp_id: str
    transaction_date: date
    type: str
    amount: float
    description: Optional[str] = ""
    category: str
    suggested_category: str
    category_confidence: float
    explanation: str
    is_reviewed: bool
    payment_method: str
    is_duplicate: bool = False
    duplicate_reason: Optional[str] = None

class ParseCsvResponse(BaseModel):
    items: List[ParseCsvItem]
    total_parsed: int
    duplicates_count: int
    needs_review_count: int

class ConfirmImportItem(BaseModel):
    transaction_date: date
    type: str
    amount: float
    description: Optional[str] = ""
    category: str
    payment_method: Optional[str] = "Bank Transfer"
    category_confidence: Optional[float] = 1.0
    is_reviewed: Optional[bool] = True

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        from services.categorization_service import ALL_VALID_CATEGORIES, normalize_category_name
        cleaned = normalize_category_name(v)
        if cleaned not in ALL_VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{v}'. Supported: {', '.join(sorted(ALL_VALID_CATEGORIES))}")
        return cleaned

class ConfirmImportRequest(BaseModel):
    transactions: List[ConfirmImportItem] = Field(default_factory=list)
    items: Optional[List[ConfirmImportItem]] = None
    skip_duplicates: bool = True

    def model_post_init(self, __context: Any) -> None:
        if not self.transactions and self.items:
            self.transactions = self.items


from schemas.notification import NotificationResponse

# Extended Dashboard Summary including transaction stats
class DashboardSummaryResponse(BaseModel):
    profile: FinancialProfileResponse
    budgets: List[BudgetResponse]
    goals: List[FinancialGoalResponse]
    insights: List[str]
    total_income: float
    total_expense: float
    savings: float
    transaction_count: int
    monthly_income: float
    monthly_expense: float
    risk_level: str
    risk_confidence: float
    health_score_grade: str
    anomalies: List[str]
    recommendations: List[str]
    forecasted_expense: float
    notifications: List[NotificationResponse]
    safe_to_spend: Optional[dict] = None
    goal_protection: Optional[List[dict]] = None
    health_breakdown: Optional[dict] = None
    structured_risks: Optional[List[dict]] = None
    next_best_actions: Optional[List[dict]] = None
    forecast_scenarios: Optional[dict] = None
    status_text: Optional[str] = None
    income_sources: Optional[List[Any]] = None
    total_monthly_income: Optional[float] = None
    one_time_available_cash: Optional[float] = 0.0
    one_time_allocated_to_goals: Optional[float] = 0.0
    one_time_free_cash: Optional[float] = 0.0
    one_time_unallocated: Optional[float] = 0.0
    forecasted_savings: Optional[float] = None

class PredictRiskRequest(BaseModel):
    income: float = Field(..., gt=0)
    expenses: float = Field(..., ge=0)
    savings: float
    debt: float = Field(..., ge=0)
    transaction_count: int = Field(..., ge=0)

class PredictRiskResponse(BaseModel):
    risk_level: str
    confidence: float
    financial_health_score: int
