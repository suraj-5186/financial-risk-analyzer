"""
Financial Insights & Cash Flow Router (Task 20)
Authenticated endpoints for cash flow analysis, deterministic forecasting, and explainable health insights.
"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.session import get_db
from models.user import User
from schemas.insights import (
    CashFlowSummaryResponse,
    CashFlowForecastResponse,
    FinancialHealthResponse,
)
from services.auth_service import get_current_user
from services.cash_flow_service import get_user_cash_flow_summary
from services.cash_flow_forecast_service import compute_cash_flow_forecast
from services.financial_insights_service import generate_financial_health_insights

router = APIRouter(prefix="/api/insights", tags=["Financial Insights & Cash Flow"])


@router.get("/cash-flow", response_model=CashFlowSummaryResponse)
def get_cash_flow_summary(
    timeframe: str = Query("30d", pattern="^(30d|month|90d|year)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns historical cash flow metrics (income, expenses, net flow, savings rate),
    6-month trend line, category breakdown, and period-over-period comparison.
    """
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be later than end_date.",
        )

    try:
        summary = get_user_cash_flow_summary(
            db=db,
            user_id=current_user.id,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate cash flow metrics: {str(e)}",
        )


@router.get("/forecast", response_model=CashFlowForecastResponse)
def get_cash_flow_forecast(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns deterministic month-end and 30-day forward cash flow forecasts.
    Isolates discretionary burn rates from known recurring commitments to eliminate double-counting.
    """
    try:
        forecast = compute_cash_flow_forecast(db=db, user_id=current_user.id)
        return forecast
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate cash flow forecast: {str(e)}",
        )


@router.get("/financial-health", response_model=FinancialHealthResponse)
def get_financial_health_insights(
    timeframe: str = Query("30d", pattern="^(30d|month|90d|year)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns rule-based, explainable financial health observations backed by actual user data,
    including spending surges, category concentration, recurring burdens, and budget overruns.
    """
    try:
        insights = generate_financial_health_insights(
            db=db,
            user_id=current_user.id,
            timeframe=timeframe,
        )
        return insights
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate financial health insights: {str(e)}",
        )
