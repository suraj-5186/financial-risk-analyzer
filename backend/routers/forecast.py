from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from models.transaction import Transaction
from models.profile import FinancialProfile
from models.goal import FinancialGoal
from services.auth_service import get_current_user
from services.financial_service import forecast_expenses_and_savings, calculate_balance_forecast_scenarios
import datetime

router = APIRouter(prefix="/api/forecast", tags=["forecast"])

@router.get("/projections")
def get_financial_projections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate next-month expense & savings projections, 6-month cashflow chart,
    goal-completion estimate, and intra-month balance scenarios for the
    authenticated user. All calculations are deterministic and backend-authoritative.
    """
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == current_user.id).first()
    income_val = profile.monthly_income if profile else 50000.0
    # Guard against None / 0 (avoids divide-by-zero in callers)
    if not income_val or income_val <= 0:
        income_val = 50000.0

    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()
    goals = db.query(FinancialGoal).filter(FinancialGoal.user_id == current_user.id).all()

    # ── All-time totals (for current-balance heuristic) ──────────────────────
    total_income = sum(t.amount for t in transactions if t.type == "Income")
    total_expense = sum(t.amount for t in transactions if t.type == "Expense")
    current_savings = total_income - total_expense

    # ── Linear-trend expense forecast ────────────────────────────────────────
    forecast = forecast_expenses_and_savings(transactions, income_val)
    proj_expense = forecast.get("forecasted_expense", 0.0)
    proj_savings = income_val - proj_expense

    # ── Risk-trend direction ──────────────────────────────────────────────────
    expense_txns = sorted(
        [t for t in transactions if t.type == "Expense"],
        key=lambda x: x.transaction_date
    )
    risk_trend = "Stable"
    if len(expense_txns) > 5:
        today = datetime.date.today()
        this_month_spent = sum(
            t.amount for t in expense_txns
            if t.transaction_date.year == today.year and t.transaction_date.month == today.month
        )
        prior_txns = [t for t in expense_txns if t.transaction_date < datetime.date(today.year, today.month, 1)]
        if prior_txns:
            # Estimate monthly average from prior transactions (15-day window approximation)
            avg_prior = sum(t.amount for t in prior_txns) / len(prior_txns) * 15
            if this_month_spent > avg_prior * 1.15:
                risk_trend = "Increasing (Expenses rising)"
            elif this_month_spent < avg_prior * 0.85:
                risk_trend = "Decreasing (Expenses falling)"

    # ── Goal-completion estimate (best active incomplete goal) ────────────────
    goal_completion_months: float = 0
    goal_completion_date: str = "N/A"
    goal_completion_title: str = "N/A"
    active_goals = [g for g in goals if g.current_amount < g.target_amount]
    if active_goals and proj_savings > 0:
        # Pick the goal that needs the least additional time
        best_goal = min(active_goals, key=lambda g: max(0.0, g.target_amount - g.current_amount))
        remaining = max(0.0, best_goal.target_amount - best_goal.current_amount)
        months_req = remaining / proj_savings
        goal_completion_months = round(months_req, 1)
        today = datetime.date.today()
        days_req = int(months_req * 30)
        target_date = today + datetime.timedelta(days=days_req)
        goal_completion_date = target_date.strftime("%B %Y")
        goal_completion_title = best_goal.title

    # ── 6-month cashflow trend (chart data) ───────────────────────────────────
    today = datetime.date.today()
    chart_data = []
    # Anchor: if no expense data yet, fall back to 60% of income
    base_exp = proj_expense if proj_expense > 0 else (income_val * 0.60)
    for i in range(1, 7):
        future_date = today + datetime.timedelta(days=i * 30)
        # 1% monthly inflation growth (linear approximation)
        factor = 1.0 + (i * 0.01)
        month_exp = round(base_exp * factor, 2)
        month_sav = round(income_val - month_exp, 2)
        chart_data.append({
            "month": future_date.strftime("%b %y"),
            "projected_income": round(income_val, 2),
            "projected_expense": month_exp,
            "projected_savings": month_sav,
        })

    # ── Intra-month balance scenarios (reuse existing financial_service fn) ───
    current_liquid = max(0.0, current_savings) if total_income > 0 else (income_val * 0.40)
    balance_scenarios = calculate_balance_forecast_scenarios(transactions, income_val, current_liquid)

    # ── Forecast assumptions metadata ────────────────────────────────────────
    expense_data_months = len({
        (t.transaction_date.year, t.transaction_date.month)
        for t in transactions if t.type == "Expense"
    })
    has_enough_history = expense_data_months >= 2

    assumptions = {
        "method": "linear_trend" if has_enough_history else "average_fallback",
        "income_source": "profile_monthly_income",
        "inflation_rate_pct": 1.0,
        "expense_data_months": expense_data_months,
        "has_sufficient_history": has_enough_history,
        "disclaimer": (
            "Projections are deterministic estimates based on your recorded transaction history "
            "and are not guaranteed future outcomes. Actual results will vary."
        ),
    }

    return {
        "projected_income": round(income_val, 2),
        "projected_expense": round(proj_expense, 2),
        "projected_savings": round(proj_savings, 2),
        "risk_trend": risk_trend,
        "goal_completion_months": goal_completion_months,
        "goal_completion_date": goal_completion_date,
        "goal_completion_title": goal_completion_title,
        "chart_data": chart_data,
        "forecast_scenarios": balance_scenarios,
        "has_sufficient_history": has_enough_history,
        "assumptions": assumptions,
    }
