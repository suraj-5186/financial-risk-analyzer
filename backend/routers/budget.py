from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from models.budget import Budget
from models.transaction import Transaction
from schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from services.auth_service import get_current_user
from services.notification_service import check_and_trigger_notifications
from services.audit_service import log_audit_event
from services.currency_utils import round_currency
import datetime

import calendar

router = APIRouter(prefix="/api/budgets", tags=["budgets"])

def get_month_date_range(month_str: Optional[str] = None):
    """Return (start_date, end_date, target_year, target_month) for calendar month filtering."""
    if month_str:
        try:
            year_val, month_val = map(int, month_str.split("-"))
            _, last_day = calendar.monthrange(year_val, month_val)
            return (
                datetime.date(year_val, month_val, 1),
                datetime.date(year_val, month_val, last_day),
                year_val,
                month_val
            )
        except Exception:
            pass
    today = datetime.date.today()
    _, last_day = calendar.monthrange(today.year, today.month)
    return (
        datetime.date(today.year, today.month, 1),
        datetime.date(today.year, today.month, last_day),
        today.year,
        today.month
    )

def calculate_budget_metrics(
    budget: Budget,
    db: Session,
    user_id: str,
    month_str: Optional[str] = None
) -> dict:
    """
    Calculate actual spending, remaining balance, and utilization percentage
    strictly scoped to the current calendar month (or specified YYYY-MM period).
    """
    start_date, end_date, target_year, target_month = get_month_date_range(month_str)

    # Count expenses strictly in this category and calendar month period for the user
    total_spent_res = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.type == "Expense",
        Transaction.category == budget.category,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date
    ).with_entities(Transaction.amount).all()

    actual_spent = round_currency(sum(t[0] for t in total_spent_res) if total_spent_res else 0.0)
    
    # Update persisted spent field for current month
    today = datetime.date.today()
    if target_year == today.year and target_month == today.month:
        if budget.spent != actual_spent:
            budget.spent = actual_spent
            db.commit()
            db.refresh(budget)

    limit = round_currency(budget.monthly_limit)
    remaining = round_currency(max(0.0, limit - actual_spent))
    utilization = round((actual_spent / limit * 100.0), 1) if limit > 0 else (100.0 if actual_spent > 0 else 0.0)

    return {
        "id": budget.id,
        "category": budget.category,
        "monthly_limit": limit,
        "spent": actual_spent,
        "remaining": remaining,
        "utilization_pct": utilization,
        "user_id": budget.user_id
    }

@router.get("", response_model=List[BudgetResponse])
def get_budgets(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    budgets = db.query(Budget).filter(Budget.user_id == current_user.id).all()
    return [calculate_budget_metrics(b, db, current_user.id, month) for b in budgets]

@router.post("", response_model=BudgetResponse)
def create_budget(
    budget_in: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if budget for this category already exists for this user
    existing = db.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.category == budget_in.category
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"A budget category for '{budget_in.category}' already exists. Please update its limit instead."
        )

    # Initial spent calculation from any existing transactions in this category for current month
    start_date, end_date, _, _ = get_month_date_range()
    total_spent_res = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "Expense",
        Transaction.category == budget_in.category,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date
    ).with_entities(Transaction.amount).all()
    initial_spent = round_currency(sum(t[0] for t in total_spent_res) if total_spent_res else 0.0)

    db_budget = Budget(
        user_id=current_user.id,
        category=budget_in.category,
        monthly_limit=round_currency(budget_in.monthly_limit),
        spent=initial_spent
    )
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)

    check_and_trigger_notifications(db, current_user.id)
    log_audit_event(db, current_user.id, "CREATE_BUDGET", f"Created budget for {db_budget.category} with limit ₹{db_budget.monthly_limit:,.2f}")
    return calculate_budget_metrics(db_budget, db, current_user.id)

@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: int,
    budget_in: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == current_user.id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
        
    old_category = budget.category
    update_data = budget_in.model_dump(exclude_unset=True)

    if "category" in update_data and update_data["category"] != old_category:
        # Check duplicate category
        dup = db.query(Budget).filter(
            Budget.user_id == current_user.id,
            Budget.category == update_data["category"],
            Budget.id != budget_id
        ).first()
        if dup:
            raise HTTPException(
                status_code=400,
                detail=f"A budget category for '{update_data['category']}' already exists."
            )

    for field, value in update_data.items():
        if field == "monthly_limit" and value is not None:
            setattr(budget, field, round_currency(value))
        else:
            setattr(budget, field, value)
        
    db.commit()
    db.refresh(budget)

    check_and_trigger_notifications(db, current_user.id)
    log_audit_event(db, current_user.id, "UPDATE_BUDGET", f"Updated budget {budget.category} limit to ₹{budget.monthly_limit:,.2f}")
    return calculate_budget_metrics(budget, db, current_user.id)

@router.delete("/{budget_id}")
def delete_budget(
    budget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Safely delete a budget category.
    Transactions assigned to this category remain intact in the ledger and are never deleted or reassigned.
    """
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == current_user.id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
        
    cat_name = budget.category
    # Check if there are associated transactions for informative feedback
    associated_count = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.category == cat_name
    ).count()

    db.delete(budget)
    db.commit()

    check_and_trigger_notifications(db, current_user.id)
    log_audit_event(db, current_user.id, "DELETE_BUDGET", f"Deleted budget category '{cat_name}'. {associated_count} associated transactions were preserved.")
    return {
        "status": "success",
        "message": f"Budget category '{cat_name}' deleted successfully. {associated_count} past transactions were safely preserved.",
        "category": cat_name,
        "preserved_transactions_count": associated_count
    }

