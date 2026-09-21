"""
Cash Flow Analysis Service (Task 20)
Analyzes historical transactions to calculate income, expenses, net cash flow,
category distributions, savings rates, and period-over-period trends while
strictly excluding internal transfers and properly accounting for refunds.
"""

import datetime
import re
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.transaction import Transaction

# Transfer pattern detection to prevent internal account movements from distorting cash flow
TRANSFER_REGEX = re.compile(
    r"\b(self\s+transfer|account\s+transfer|inter[-\s]account|transfer\s+to\s+savings|transfer\s+from|funds\s+transfer|own\s+account|sweep\s+in|sweep\s+out)\b",
    re.IGNORECASE,
)


def is_internal_transfer(tx: Transaction) -> bool:
    """Identifies whether a transaction is an internal transfer between user accounts."""
    if tx.type == "Transfer" or (tx.category and tx.category.strip().lower() in ("transfers", "transfer")):
        return True
    if tx.description and TRANSFER_REGEX.search(tx.description):
        return True
    return False


def resolve_date_windows(
    timeframe: str = "30d",
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
) -> Tuple[datetime.date, datetime.date, datetime.date, datetime.date]:
    """
    Returns (current_start, current_end, previous_start, previous_end)
    for period-over-period comparative analysis.
    """
    today = datetime.date.today()

    if start_date and end_date:
        cur_start = start_date
        cur_end = end_date
        span = (cur_end - cur_start).days + 1
        prev_end = cur_start - datetime.timedelta(days=1)
        prev_start = prev_end - datetime.timedelta(days=span - 1)
        return cur_start, cur_end, prev_start, prev_end

    tf = timeframe.lower()
    if tf == "month":
        # Current month to date
        cur_start = datetime.date(today.year, today.month, 1)
        cur_end = today
        # Previous month
        prev_m = today.month - 1 if today.month > 1 else 12
        prev_y = today.year if today.month > 1 else today.year - 1
        prev_start = datetime.date(prev_y, prev_m, 1)
        # Previous month equivalent day
        import calendar
        _, max_prev_days = calendar.monthrange(prev_y, prev_m)
        prev_day = min(today.day, max_prev_days)
        prev_end = datetime.date(prev_y, prev_m, prev_day)
    elif tf == "90d":
        cur_end = today
        cur_start = today - datetime.timedelta(days=89)
        prev_end = cur_start - datetime.timedelta(days=1)
        prev_start = prev_end - datetime.timedelta(days=89)
    elif tf == "year":
        cur_end = today
        cur_start = today - datetime.timedelta(days=364)
        prev_end = cur_start - datetime.timedelta(days=1)
        prev_start = prev_end - datetime.timedelta(days=364)
    else:
        # Default: 30 days
        cur_end = today
        cur_start = today - datetime.timedelta(days=29)
        prev_end = cur_start - datetime.timedelta(days=1)
        prev_start = prev_end - datetime.timedelta(days=29)

    return cur_start, cur_end, prev_start, prev_end


def compute_cash_flow_for_window(
    transactions: List[Transaction],
    start_date: datetime.date,
    end_date: datetime.date,
) -> Dict[str, Any]:
    """Calculates income, expenses, and category distributions for a slice of transactions."""
    income_total = 0.0
    expense_total = 0.0
    category_totals: Dict[str, float] = {}
    category_counts: Dict[str, int] = {}
    included_tx_count = 0

    for tx in transactions:
        if not (start_date <= tx.transaction_date <= end_date):
            continue
        if is_internal_transfer(tx):
            continue

        raw_amt = float(tx.amount)
        desc = (tx.description or "").lower()
        is_refund = "refund" in desc or "reversal" in desc or "rebate" in desc

        if tx.type == "Income":
            if is_refund and (tx.category not in ["Salary", "Freelance", "Business", "Investment"]):
                cat = tx.category or "Other"
                expense_total = max(0.0, expense_total - raw_amt)
                category_totals[cat] = max(0.0, category_totals.get(cat, 0.0) - raw_amt)
            else:
                income_total += raw_amt
            included_tx_count += 1
        elif tx.type == "Expense":
            cat = tx.category or "Other"
            if raw_amt >= 0:
                expense_total += raw_amt
                category_totals[cat] = category_totals.get(cat, 0.0) + raw_amt
                category_counts[cat] = category_counts.get(cat, 0) + 1
            else:
                # Negative expense represents a refund/credit adjustment
                expense_total = max(0.0, expense_total + raw_amt)
                category_totals[cat] = max(0.0, category_totals.get(cat, 0.0) + raw_amt)
            included_tx_count += 1

    income_total = round(max(0.0, income_total), 2)
    expense_total = round(max(0.0, expense_total), 2)
    net_flow = round(income_total - expense_total, 2)
    savings_rate = round((net_flow / income_total) * 100.0, 1) if income_total > 0 else None

    # Sort categories by spending descending
    categories_list = []
    for cat, amt in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
        if amt > 0:
            pct = round((amt / expense_total) * 100.0, 1) if expense_total > 0 else 0.0
            categories_list.append({
                "category": cat,
                "amount": round(amt, 2),
                "percentage": pct,
                "transaction_count": category_counts.get(cat, 0),
            })

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_income": income_total,
        "total_expenses": expense_total,
        "net_cash_flow": net_flow,
        "savings_rate": savings_rate,
        "transaction_count": included_tx_count,
        "categories": categories_list,
    }


def compute_monthly_trends(transactions: List[Transaction], num_months: int = 6) -> List[Dict[str, Any]]:
    """Builds chronological month-by-month cash flow trend series."""
    today = datetime.date.today()
    # Collect list of YYYY-MM
    months = []
    y, m = today.year, today.month
    for _ in range(num_months):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m < 1:
            m = 12
            y -= 1
    months.reverse()

    monthly_map: Dict[str, Dict[str, float]] = {
        mo: {"income": 0.0, "expenses": 0.0} for mo in months
    }

    for tx in transactions:
        if is_internal_transfer(tx):
            continue
        key = tx.transaction_date.strftime("%Y-%m")
        if key in monthly_map:
            amt = float(tx.amount)
            if tx.type == "Income":
                monthly_map[key]["income"] += amt
            elif tx.type == "Expense":
                monthly_map[key]["expenses"] += amt

    trend_points = []
    for mo in months:
        inc = round(max(0.0, monthly_map[mo]["income"]), 2)
        exp = round(max(0.0, monthly_map[mo]["expenses"]), 2)
        net = round(inc - exp, 2)
        # Parse month label e.g. "Sep 2026"
        dt = datetime.datetime.strptime(mo, "%Y-%m")
        trend_points.append({
            "month_key": mo,
            "month_label": dt.strftime("%b %Y"),
            "income": inc,
            "expenses": exp,
            "net_cash_flow": net,
        })

    return trend_points


def get_user_cash_flow_summary(
    db: Session,
    user_id: str,
    timeframe: str = "30d",
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
) -> Dict[str, Any]:
    """
    Main entry point for historical cash flow metrics, trends, category distributions,
    and period-over-period comparative analysis.
    """
    cur_start, cur_end, prev_start, prev_end = resolve_date_windows(timeframe, start_date, end_date)

    # Fetch all user transactions to compute current, previous, and 6-month trends
    all_txs = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.asc())
        .all()
    )

    current_data = compute_cash_flow_for_window(all_txs, cur_start, cur_end)
    prev_data = compute_cash_flow_for_window(all_txs, prev_start, prev_end)
    trends = compute_monthly_trends(all_txs, num_months=6)

    # Calculate Period-over-Period Deltas
    def pct_change(cur: float, prev: float) -> Optional[float]:
        if prev == 0:
            return None if cur == 0 else 100.0
        return round(((cur - prev) / abs(prev)) * 100.0, 1)

    income_delta = pct_change(current_data["total_income"], prev_data["total_income"])
    expense_delta = pct_change(current_data["total_expenses"], prev_data["total_expenses"])
    net_delta = pct_change(current_data["net_cash_flow"], prev_data["net_cash_flow"])

    return {
        "timeframe": timeframe,
        "period_start": cur_start,
        "period_end": cur_end,
        "previous_period_start": prev_start,
        "previous_period_end": prev_end,
        "total_income": current_data["total_income"],
        "total_expenses": current_data["total_expenses"],
        "net_cash_flow": current_data["net_cash_flow"],
        "savings_rate": current_data["savings_rate"],
        "transaction_count": current_data["transaction_count"],
        "categories": current_data["categories"],
        "trends": trends,
        "comparison": {
            "previous_income": prev_data["total_income"],
            "previous_expenses": prev_data["total_expenses"],
            "previous_net_cash_flow": prev_data["net_cash_flow"],
            "income_change_pct": income_delta,
            "expense_change_pct": expense_delta,
            "net_flow_change_pct": net_delta,
        },
    }
