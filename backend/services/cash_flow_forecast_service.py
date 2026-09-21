"""
Cash Flow Forecasting Service (Task 20)
Generates transparent, deterministic month-end and 30-day cash flow projections
by isolating variable discretionary burn rates from confirmed recurring commitments,
thereby strictly avoiding double-counting.
"""

import datetime
import calendar
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from models.transaction import Transaction
from models.recurring_payment import RecurringPayment
from models.profile import FinancialProfile
from services.cash_flow_service import is_internal_transfer


def compute_cash_flow_forecast(
    db: Session,
    user_id: str,
) -> Dict[str, Any]:
    """
    Computes deterministic month-end and 30-day cash flow projections.
    Forecasts are strictly labeled as estimates and backed by clear mathematical factors.
    """
    today = datetime.date.today()
    cur_year = today.year
    cur_month = today.month

    # Days in current month
    _, max_month_days = calendar.monthrange(cur_year, cur_month)
    days_elapsed = today.day
    days_remaining = max_month_days - days_elapsed
    month_end_date = datetime.date(cur_year, cur_month, max_month_days)
    next_30_date = today + datetime.timedelta(days=30)

    # 1. Fetch user transactions (lookback up to 90 days)
    lookback_start = today - datetime.timedelta(days=90)
    txs = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= lookback_start,
            Transaction.transaction_date <= today,
        )
        .order_by(Transaction.transaction_date.asc())
        .all()
    )

    # Filter out internal transfers
    valid_txs = [t for t in txs if not is_internal_transfer(t)]

    # 2. Fetch user's active recurring payments (Task 18)
    recurring_items = (
        db.query(RecurringPayment)
        .filter(
            RecurringPayment.user_id == user_id,
            RecurringPayment.status.in_(["confirmed", "detected"]),
        )
        .all()
    )

    # 3. Assess Data Quality & Confidence
    tx_count = len(valid_txs)
    if tx_count == 0:
        span_days = 0
    else:
        first_date = valid_txs[0].transaction_date
        span_days = (today - first_date).days + 1

    if tx_count < 3 or span_days < 7:
        data_quality = "insufficient"
        confidence_score = 0.25
        confidence_label = "Insufficient History"
    elif tx_count < 8 or span_days < 25:
        data_quality = "low"
        confidence_score = 0.55
        confidence_label = "Low Confidence (Limited History)"
    elif span_days < 60 or tx_count < 15:
        data_quality = "medium"
        confidence_score = 0.78
        confidence_label = "Medium Confidence"
    else:
        data_quality = "high"
        confidence_score = 0.90
        confidence_label = "High Confidence"

    # 4. Current Month Actuals
    month_start = datetime.date(cur_year, cur_month, 1)
    month_income_actual = sum(
        float(t.amount) for t in valid_txs
        if t.type == "Income" and t.transaction_date >= month_start
    )
    month_expense_actual = sum(
        float(t.amount) for t in valid_txs
        if t.type == "Expense" and t.transaction_date >= month_start
    )

    # 5. Baseline Discretionary Burn Rate Calculation (Excluding Recurring)
    # Identify known recurring payment merchants
    recurring_normalized_names = {r.normalized_name for r in recurring_items}
    total_recurring_monthly_cost = sum(r.estimated_monthly_cost for r in recurring_items)

    # Calculate discretionary expenses over the lookback period
    discretionary_expenses_total = 0.0
    for t in valid_txs:
        if t.type == "Expense":
            # Check if description matches any known recurring normalized name
            desc_lower = (t.description or "").lower()
            is_rec = any(name in desc_lower for name in recurring_normalized_names)
            if not is_rec:
                discretionary_expenses_total += float(t.amount)

    effective_span = max(1, span_days)
    daily_discretionary_burn = round(discretionary_expenses_total / effective_span, 2)

    # 6. Upcoming Recurring Commitments Due Before Month-End
    upcoming_month_end_recurring: List[Dict[str, Any]] = []
    recurring_cost_month_end = 0.0

    for r in recurring_items:
        if r.next_estimated_date and today < r.next_estimated_date <= month_end_date:
            upcoming_month_end_recurring.append({
                "merchant_name": r.merchant_name,
                "amount": r.last_amount,
                "due_date": r.next_estimated_date,
                "frequency": r.frequency,
            })
            recurring_cost_month_end += float(r.last_amount)

    # 7. Upcoming Recurring Commitments in Next 30 Days
    upcoming_30d_recurring: List[Dict[str, Any]] = []
    recurring_cost_30d = 0.0

    for r in recurring_items:
        if r.next_estimated_date and today < r.next_estimated_date <= next_30_date:
            upcoming_30d_recurring.append({
                "merchant_name": r.merchant_name,
                "amount": r.last_amount,
                "due_date": r.next_estimated_date,
                "frequency": r.frequency,
            })
            recurring_cost_30d += float(r.last_amount)

    # 8. Projected Month-End Expenses
    projected_additional_discretionary_month_end = round(daily_discretionary_burn * days_remaining, 2)
    projected_total_month_expense = round(
        month_expense_actual + projected_additional_discretionary_month_end + recurring_cost_month_end,
        2,
    )

    # 9. Projected Month-End Income
    # Check profile monthly income or historical monthly average
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == user_id).first()
    expected_monthly_income = profile.monthly_income if (profile and profile.monthly_income and profile.monthly_income > 0) else None

    if expected_monthly_income:
        # If actual income received so far is less than expected base income, assume remainder will be received
        projected_additional_income = max(0.0, float(expected_monthly_income) - month_income_actual)
        projected_total_month_income = round(month_income_actual + projected_additional_income, 2)
    else:
        # If no profile income, extrapolate historical monthly average
        hist_incomes = [float(t.amount) for t in valid_txs if t.type == "Income"]
        if hist_incomes:
            avg_income_per_day = sum(hist_incomes) / effective_span
            projected_additional_income = round(avg_income_per_day * days_remaining, 2)
            projected_total_month_income = round(month_income_actual + projected_additional_income, 2)
        else:
            projected_additional_income = 0.0
            projected_total_month_income = round(month_income_actual, 2)

    projected_month_end_net_cash_flow = round(projected_total_month_income - projected_total_month_expense, 2)

    # 10. Next 30-Day Forward Projections
    next_30d_discretionary = round(daily_discretionary_burn * 30, 2)
    next_30d_projected_expense = round(next_30d_discretionary + recurring_cost_30d, 2)
    next_30d_projected_income = round((expected_monthly_income or (projected_total_month_income or 0.0)), 2)
    next_30d_net_cash_flow = round(next_30d_projected_income - next_30d_projected_expense, 2)

    # 11. Explanatory Breakdown
    explanations = [
        f"Analyzed {tx_count} transactions spanning {span_days} days of activity.",
        f"Estimated baseline discretionary daily spending rate at ₹{daily_discretionary_burn:,.2f}/day (excluding recurring commitments).",
        f"Identified {len(upcoming_month_end_recurring)} scheduled recurring bills totaling ₹{recurring_cost_month_end:,.2f} due before month-end.",
        f"{days_remaining} days remaining in current calendar month.",
    ]
    if expected_monthly_income:
        explanations.append(f"Referenced configured monthly income profile (₹{expected_monthly_income:,.2f}) for income baseline.")

    return {
        "as_of_date": today,
        "data_quality": data_quality,
        "confidence_score": confidence_score,
        "confidence_label": confidence_label,
        "is_estimate": True,
        "month_end_forecast": {
            "month_label": today.strftime("%B %Y"),
            "days_remaining": days_remaining,
            "actual_income_to_date": round(month_income_actual, 2),
            "actual_expense_to_date": round(month_expense_actual, 2),
            "projected_additional_discretionary": projected_additional_discretionary_month_end,
            "projected_additional_recurring": round(recurring_cost_month_end, 2),
            "projected_total_expenses": projected_total_month_expense,
            "projected_total_income": projected_total_month_income,
            "projected_net_cash_flow": projected_month_end_net_cash_flow,
            "upcoming_recurring_commitments": upcoming_month_end_recurring,
        },
        "next_30_days_forecast": {
            "projected_income": next_30d_projected_income,
            "projected_discretionary_expense": next_30d_discretionary,
            "projected_recurring_expense": round(recurring_cost_30d, 2),
            "projected_total_expense": next_30d_projected_expense,
            "projected_net_cash_flow": next_30d_net_cash_flow,
            "upcoming_recurring_count": len(upcoming_30d_recurring),
        },
        "methodology": {
            "daily_discretionary_burn": daily_discretionary_burn,
            "total_monthly_recurring_commitments": round(total_recurring_monthly_cost, 2),
            "explanations": explanations,
            "disclaimer": "All forecasts are mathematical projections based on historical patterns and recurring obligations. They do not constitute guaranteed account balances or financial advice.",
        },
    }
