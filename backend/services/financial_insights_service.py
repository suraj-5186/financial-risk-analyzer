"""
Financial Health Insights Engine (Task 20)
Generates rule-based, explainable financial observations backed by actual user data,
including spending spikes, category concentration, recurring burdens, and budget overruns.
"""

import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from models.transaction import Transaction
from models.budget import Budget
from models.recurring_payment import RecurringPayment
from models.profile import FinancialProfile
from services.cash_flow_service import get_user_cash_flow_summary


def generate_financial_health_insights(
    db: Session,
    user_id: str,
    timeframe: str = "30d",
) -> Dict[str, Any]:
    """
    Evaluates rule-based insight heuristics against verified ledger and budget data.
    Every insight provides explicit period details, numerical impacts, and calculation explanations.
    """
    # 1. Fetch cash flow summary
    cash_flow = get_user_cash_flow_summary(db, user_id, timeframe=timeframe)
    cur_income = cash_flow["total_income"]
    cur_expenses = cash_flow["total_expenses"]
    net_flow = cash_flow["net_cash_flow"]
    savings_rate = cash_flow["savings_rate"]
    categories = cash_flow["categories"]
    comparison = cash_flow["comparison"]

    period_label = f"{cash_flow['period_start'].strftime('%b %d')} – {cash_flow['period_end'].strftime('%b %d, %Y')}"
    prev_period_label = f"{cash_flow['previous_period_start'].strftime('%b %d')} – {cash_flow['previous_period_end'].strftime('%b %d, %Y')}"

    # 2. Fetch user budgets and recurring items
    budgets = db.query(Budget).filter(Budget.user_id == user_id).all()
    recurring_items = (
        db.query(RecurringPayment)
        .filter(
            RecurringPayment.user_id == user_id,
            RecurringPayment.status.in_(["confirmed", "detected"]),
        )
        .all()
    )
    total_recurring_monthly = sum(r.estimated_monthly_cost for r in recurring_items)

    insights: List[Dict[str, Any]] = []

    # ── Rule 1: Cash Flow Deficit ─────────────────────────────────────────────
    if cur_expenses > cur_income and cur_expenses > 0:
        deficit_amt = round(cur_expenses - cur_income, 2)
        insights.append({
            "id": "insight_cash_flow_deficit",
            "type": "risk",
            "title": "Cash Flow Deficit Warning",
            "description": f"Expenses exceeded income by ₹{deficit_amt:,.2f} over the analyzed period.",
            "period": period_label,
            "metric_impact": f"-₹{deficit_amt:,.2f}",
            "explanation": f"Total expenses of ₹{cur_expenses:,.2f} outpaced total income of ₹{cur_income:,.2f}, resulting in a negative net cash flow.",
            "recommended_action": "Pause discretionary purchases and review upcoming bill commitments to restore cash flow parity.",
        })

    # ── Rule 2: Spending Surge / Velocity Spike ──────────────────────────────
    expense_pct_change = comparison.get("expense_change_pct")
    prev_expenses = comparison.get("previous_expenses", 0.0)
    if expense_pct_change is not None and expense_pct_change >= 15.0 and (cur_expenses - prev_expenses) >= 1000.0:
        extra_spent = round(cur_expenses - prev_expenses, 2)
        insights.append({
            "id": "insight_spending_surge",
            "type": "warning",
            "title": "Spending Velocity Surge",
            "description": f"Expenditures increased by {expense_pct_change:.1f}% compared with the prior equivalent period.",
            "period": f"{period_label} vs {prev_period_label}",
            "metric_impact": f"+{expense_pct_change:.1f}% (₹{extra_spent:,.2f})",
            "explanation": f"Current spending reached ₹{cur_expenses:,.2f}, up from ₹{prev_expenses:,.2f} in the previous period.",
            "recommended_action": "Audit recent transactions to distinguish planned one-off commitments from lifestyle creep.",
        })

    # ── Rule 3: Category Spending Concentration ──────────────────────────────
    if categories and cur_expenses >= 2000.0:
        top_cat = categories[0]
        # Ignore Rent/Housing from concentration alert as rent is naturally high
        if top_cat["category"] not in ("Rent", "Housing") and top_cat["percentage"] >= 35.0:
            insights.append({
                "id": f"insight_category_concentration_{top_cat['category'].lower().replace(' ', '_')}",
                "type": "warning",
                "title": f"High Concentration in {top_cat['category']}",
                "description": f"{top_cat['category']} represents {top_cat['percentage']:.1f}% of your total outflow.",
                "period": period_label,
                "metric_impact": f"{top_cat['percentage']:.1f}% of spend",
                "explanation": f"₹{top_cat['amount']:,.2f} out of ₹{cur_expenses:,.2f} total expenses was spent in {top_cat['category']} across {top_cat['transaction_count']} transactions.",
                "recommended_action": f"Review variable expenses in {top_cat['category']} to balance category distribution.",
            })

    # ── Rule 4: Recurring Commitments Burden ─────────────────────────────────
    if total_recurring_monthly > 0 and cur_expenses >= 2000.0:
        recurring_ratio = (total_recurring_monthly / cur_expenses) * 100.0
        if recurring_ratio >= 35.0:
            insights.append({
                "id": "insight_recurring_burden",
                "type": "warning",
                "title": "High Fixed Recurring Commitments",
                "description": f"Fixed subscriptions and recurring utilities account for {recurring_ratio:.1f}% of your monthly outflow.",
                "period": "Monthly Run-Rate",
                "metric_impact": f"₹{total_recurring_monthly:,.2f}/mo ({recurring_ratio:.1f}%)",
                "explanation": f"Detected {len(recurring_items)} recurring commitments totaling ₹{total_recurring_monthly:,.2f}/month against monthly expenses of ₹{cur_expenses:,.2f}.",
                "recommended_action": "Open Subscriptions to review and cancel inactive streaming, software, or service memberships.",
            })

    # ── Rule 5: Budget Overrun Alerts ────────────────────────────────────────
    for b in budgets:
        # Match current period expenses for this budget category
        cat_match = next((c for c in categories if c["category"].lower() == b.category.lower()), None)
        cat_spent = cat_match["amount"] if cat_match else 0.0
        b_limit = float(b.monthly_limit)
        if b_limit > 0 and cat_spent > b_limit:
            over_amt = round(cat_spent - b_limit, 2)
            over_pct = round((cat_spent / b_limit) * 100.0, 1)
            insights.append({
                "id": f"insight_budget_overrun_{b.category.lower().replace(' ', '_')}",
                "type": "risk",
                "title": f"Budget Exceeded in {b.category}",
                "description": f"Spending in {b.category} is {over_pct:.1f}% of configured limit (over by ₹{over_amt:,.2f}).",
                "period": period_label,
                "metric_impact": f"+{over_pct - 100.0:.1f}% over limit",
                "explanation": f"Actual expenditures in {b.category} totaled ₹{cat_spent:,.2f} versus your configured monthly target of ₹{b_limit:,.2f}.",
                "recommended_action": f"Freeze discretionary purchases in {b.category} until the next budget cycle.",
            })

    # ── Rule 6: Positive Savings Momentum ────────────────────────────────────
    if savings_rate is not None and savings_rate >= 20.0 and net_flow >= 1000.0:
        insights.append({
            "id": "insight_savings_surplus",
            "type": "achievement",
            "title": "Strong Capital Surplus",
            "description": f"Achieved a {savings_rate:.1f}% savings rate with a net surplus of ₹{net_flow:,.2f}.",
            "period": period_label,
            "metric_impact": f"{savings_rate:.1f}% Savings Rate",
            "explanation": f"Total income of ₹{cur_income:,.2f} significantly exceeded outflow of ₹{cur_expenses:,.2f}.",
            "recommended_action": "Allocate a portion of this cash flow surplus toward your primary savings goal or emergency reserves.",
        })

    # Compute overall health status grade
    if any(i["type"] == "risk" for i in insights):
        overall_health = "Attention Recommended"
        health_tone = "risk"
    elif any(i["type"] == "warning" for i in insights):
        overall_health = "Moderate with Observations"
        health_tone = "warning"
    elif any(i["type"] == "achievement" for i in insights):
        overall_health = "Strong & Stable"
        health_tone = "healthy"
    else:
        overall_health = "Stable Baseline"
        health_tone = "info"

    return {
        "as_of_date": datetime.date.today(),
        "timeframe": timeframe,
        "overall_health": overall_health,
        "health_tone": health_tone,
        "total_insights_count": len(insights),
        "insights": insights,
    }
