"""
Pydantic Schemas for Cash Flow Forecasting & Financial Health Insights (Task 20)
"""

from datetime import date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class CategorySpendItem(BaseModel):
    category: str
    amount: float
    percentage: float
    transaction_count: int


class CashFlowTrendPoint(BaseModel):
    month_key: str
    month_label: str
    income: float
    expenses: float
    net_cash_flow: float


class CashFlowComparison(BaseModel):
    previous_income: float
    previous_expenses: float
    previous_net_cash_flow: float
    income_change_pct: Optional[float] = None
    expense_change_pct: Optional[float] = None
    net_flow_change_pct: Optional[float] = None


class CashFlowSummaryResponse(BaseModel):
    timeframe: str
    period_start: date
    period_end: date
    previous_period_start: date
    previous_period_end: date
    total_income: float
    total_expenses: float
    net_cash_flow: float
    savings_rate: Optional[float] = None
    transaction_count: int
    categories: List[CategorySpendItem]
    trends: List[CashFlowTrendPoint]
    comparison: CashFlowComparison


class RecurringCommitmentDue(BaseModel):
    merchant_name: str
    amount: float
    due_date: date
    frequency: str


class MonthEndForecast(BaseModel):
    month_label: str
    days_remaining: int
    actual_income_to_date: float
    actual_expense_to_date: float
    projected_additional_discretionary: float
    projected_additional_recurring: float
    projected_total_expenses: float
    projected_total_income: float
    projected_net_cash_flow: float
    upcoming_recurring_commitments: List[RecurringCommitmentDue]


class Next30DaysForecast(BaseModel):
    projected_income: float
    projected_discretionary_expense: float
    projected_recurring_expense: float
    projected_total_expense: float
    projected_net_cash_flow: float
    upcoming_recurring_count: int


class ForecastMethodology(BaseModel):
    daily_discretionary_burn: float
    total_monthly_recurring_commitments: float
    explanations: List[str]
    disclaimer: str


class CashFlowForecastResponse(BaseModel):
    as_of_date: date
    data_quality: str
    confidence_score: float
    confidence_label: str
    is_estimate: bool
    month_end_forecast: MonthEndForecast
    next_30_days_forecast: Next30DaysForecast
    methodology: ForecastMethodology


class FinancialInsightItem(BaseModel):
    id: str
    type: str  # risk, warning, opportunity, achievement, info
    title: str
    description: str
    period: str
    metric_impact: str
    explanation: str
    recommended_action: str


class FinancialHealthResponse(BaseModel):
    as_of_date: date
    timeframe: str
    overall_health: str
    health_tone: str
    total_insights_count: int
    insights: List[FinancialInsightItem]
