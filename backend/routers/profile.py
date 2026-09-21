import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from models.profile import FinancialProfile
from models.budget import Budget
from models.goal import FinancialGoal
from models.transaction import Transaction
from models.notification import Notification
from models.income_source import IncomeSource
from schemas.profile import FinancialProfileResponse, FinancialProfileUpdate
from schemas.transaction import DashboardSummaryResponse
from services.auth_service import get_current_user
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from ml.predict import predict_financial_risk

from services.financial_service import (
    calculate_weighted_health_score, detect_anomalies,
    forecast_expenses_and_savings, generate_insights_and_recommendations,
    calculate_safe_to_spend, calculate_goal_protection_status,
    calculate_balance_forecast_scenarios, generate_structured_risks_and_actions
)
from services.notification_service import check_and_trigger_notifications

router = APIRouter(prefix="/api/financials", tags=["profile"])

@router.get("/profile", response_model=FinancialProfileResponse)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == current_user.id).first()
    if not profile:
        profile = FinancialProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

@router.put("/profile", response_model=FinancialProfileResponse)
def update_profile(
    profile_in: FinancialProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == current_user.id).first()
    if not profile:
        profile = FinancialProfile(user_id=current_user.id)
        db.add(profile)
        
    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
        
    profile.health_score = calculate_weighted_health_score(profile)["score"]
    db.commit()
    db.refresh(profile)
    return profile

@router.get("/safe-to-spend")
def get_safe_to_spend_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == current_user.id).first()
    if not profile:
        profile = FinancialProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
    budgets = db.query(Budget).filter(Budget.user_id == current_user.id).all()
    goals = db.query(FinancialGoal).filter(FinancialGoal.user_id == current_user.id).all()
    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()
    income_sources = db.query(IncomeSource).filter(IncomeSource.user_id == current_user.id, IncomeSource.is_active == True).all()
    
    return calculate_safe_to_spend(profile, budgets, goals, transactions, income_sources)

@router.get("/goal-protection")
def get_goal_protection_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == current_user.id).first()
    if not profile:
        profile = FinancialProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
    goals = db.query(FinancialGoal).filter(FinancialGoal.user_id == current_user.id).all()
    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()
    
    return calculate_goal_protection_status(goals, profile, transactions)

@router.get("/summary", response_model=DashboardSummaryResponse)
def get_financial_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == current_user.id).first()
    if not profile:
        profile = FinancialProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
    budgets = db.query(Budget).filter(Budget.user_id == current_user.id).all()
    from routers.budget import calculate_budget_metrics
    enriched_budgets = [calculate_budget_metrics(b, db, current_user.id) for b in budgets]
    goals = db.query(FinancialGoal).filter(FinancialGoal.user_id == current_user.id).all()
    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()
    income_sources = db.query(IncomeSource).filter(IncomeSource.user_id == current_user.id).all()
    active_income_sources = [s for s in income_sources if s.is_active]
    
    # 1. Health Score & Explainable Breakdown
    health_res = calculate_weighted_health_score(profile)
    profile.health_score = health_res["score"]
    db.commit()
    
    # 2. Transaction Totals & Savings
    total_income = sum(t.amount for t in transactions if t.type == "Income")
    total_expense = sum(t.amount for t in transactions if t.type == "Expense")
    savings = total_income - total_expense
    transaction_count = len(transactions)
    
    # 3. Anomaly Detection
    anomalies = detect_anomalies(transactions)
    
    # 4. Safe to Spend (uses income sources if available)
    safe_to_spend_data = calculate_safe_to_spend(profile, budgets, goals, transactions, active_income_sources)
    
    # 5. Goal Protection Statuses
    goal_protection_data = calculate_goal_protection_status(goals, profile, transactions)
    
    # 6. Future Balance Forecast & Scenarios
    current_liquid = max(0.0, savings) if total_income > 0 else profile.monthly_income * 0.40
    forecast_scenarios_data = calculate_balance_forecast_scenarios(transactions, profile.monthly_income, current_liquid)
    
    # 7. Structured Risks & Next Best Actions (filtered for dismissed actions, enriched with is_applied)
    from models.recommendation import Recommendation
    dismissed_recs = db.query(Recommendation.id).filter(
        Recommendation.user_id == current_user.id,
        Recommendation.is_dismissed == True
    ).all()
    dismissed_ids = set()
    for r in dismissed_recs:
        rid = r[0]
        dismissed_ids.add(rid)
        if "_" in rid:
            dismissed_ids.add(rid.split("_", 1)[1])

    applied_recs = db.query(Recommendation.id).filter(
        Recommendation.user_id == current_user.id,
        Recommendation.is_applied == True
    ).all()
    applied_ids = set()
    for r in applied_recs:
        rid = r[0]
        applied_ids.add(rid)
        if "_" in rid:
            applied_ids.add(rid.split("_", 1)[1])
    
    structured_data = generate_structured_risks_and_actions(profile, goals, budgets, transactions, anomalies)
    active_actions = []
    for a in structured_data.get("actions", []):
        aid = a.get("id")
        if aid not in dismissed_ids:
            a_copy = dict(a)
            a_copy["is_applied"] = aid in applied_ids
            active_actions.append(a_copy)

    # 8. Compute strictly Recurring Monthly Income (One-time income strictly excluded)
    active_recurring = [s for s in active_income_sources if getattr(s, "income_type", "recurring") == "recurring"]
    if active_recurring:
        recurring_sum = sum(
            s.amount for s in active_recurring if s.frequency == "monthly"
        ) + sum(
            s.amount * 4.33 for s in active_recurring if s.frequency == "weekly"
        )
        total_monthly_income = round(recurring_sum, 2) if recurring_sum > 0 else (profile.monthly_income or 50000.0)
    else:
        total_monthly_income = profile.monthly_income or 50000.0

    # 9. Compute One-Time Cash Metrics (Isolated from monthly income)
    active_one_time = [s for s in active_income_sources if getattr(s, "income_type", "recurring") == "one_time"]
    one_time_available_cash = sum(s.amount for s in active_one_time)
    one_time_allocated_to_goals = 0.0
    one_time_free_cash = 0.0

    for ots in active_one_time:
        if hasattr(ots, "allocations") and ots.allocations:
            for a in ots.allocations:
                if getattr(a, "allocation_type", "") == "GOAL":
                    one_time_allocated_to_goals += a.amount
                elif getattr(a, "allocation_type", "") == "FREE_CASH":
                    one_time_free_cash += a.amount

    one_time_unallocated = max(0.0, one_time_available_cash - one_time_allocated_to_goals - one_time_free_cash)

    # 10. Legacy Diagnostics
    diagnostics = generate_insights_and_recommendations(profile, budgets, anomalies)
    insights = diagnostics["insights"]
    recommendations = diagnostics["recommendations"]

    # 11. Legacy Forecast
    forecast = forecast_expenses_and_savings(transactions, total_monthly_income)

    # 12. ML Risk Prediction
    try:
        inc = total_income if total_income > 0 else total_monthly_income
        exp = total_expense if total_expense > 0 else (inc * (1.0 - profile.savings_rate/100.0))
        sav = savings if total_income > 0 else (inc * profile.savings_rate/100.0)
        debt = (profile.debt_ratio / 100.0) * inc

        prediction = predict_financial_risk({
            "income": inc,
            "expenses": exp,
            "savings": sav,
            "debt": debt,
            "transaction_count": transaction_count
        })
        risk_level = prediction["risk_level"]
        risk_confidence = prediction["confidence"]
    except Exception:
        risk_level = "Low"
        risk_confidence = 1.0

    # 13. Current month stats
    today = datetime.date.today()
    monthly_income = sum(t.amount for t in transactions if t.type == "Income" and t.transaction_date.year == today.year and t.transaction_date.month == today.month)
    monthly_expense = sum(t.amount for t in transactions if t.type == "Expense" and t.transaction_date.year == today.year and t.transaction_date.month == today.month)

    # 14. Trigger notifications & fetch
    check_and_trigger_notifications(db, current_user.id)
    notifications_list = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).all()

    enriched_income_sources = []
    for s in income_sources:
        alloc_goals = 0.0
        free_c = 0.0
        if hasattr(s, "allocations") and s.allocations:
            for a in s.allocations:
                if getattr(a, "allocation_type", "") == "GOAL":
                    alloc_goals += a.amount
                elif getattr(a, "allocation_type", "") == "FREE_CASH":
                    free_c += a.amount
        unalloc = max(0.0, s.amount - alloc_goals - free_c)
        enriched_income_sources.append({
            "id": s.id,
            "name": s.name,
            "amount": round(s.amount, 2),
            "income_type": getattr(s, "income_type", "recurring"),
            "frequency": s.frequency,
            "is_recurring": s.is_recurring,
            "is_active": s.is_active,
            "next_expected_date": s.next_expected_date.isoformat() if s.next_expected_date else None,
            "allocated_to_goals": round(alloc_goals, 2),
            "free_cash": round(free_c, 2),
            "unallocated_amount": round(unalloc, 2),
        })

    return {
        "profile": profile,
        "budgets": enriched_budgets,
        "goals": goals,
        "insights": insights,
        "total_income": total_income,
        "total_expense": total_expense,
        "savings": savings,
        "transaction_count": transaction_count,
        "monthly_income": monthly_income,
        "monthly_expense": monthly_expense,
        "risk_level": risk_level,
        "risk_confidence": risk_confidence,
        "health_score_grade": health_res["grade"],
        "status_text": health_res.get("status_text", "You're doing well"),
        "anomalies": anomalies,
        "recommendations": recommendations,
        "forecasted_expense": forecast["forecasted_expense"],
        "forecasted_savings": forecast["forecasted_savings"],
        "notifications": notifications_list,
        "safe_to_spend": safe_to_spend_data,
        "goal_protection": goal_protection_data,
        "health_breakdown": health_res.get("breakdown"),
        "structured_risks": structured_data.get("risks", []),
        "next_best_actions": active_actions,
        "forecast_scenarios": forecast_scenarios_data,
        "income_sources": enriched_income_sources,
        "total_monthly_income": round(total_monthly_income, 2),
        "one_time_available_cash": round(one_time_available_cash, 2),
        "one_time_allocated_to_goals": round(one_time_allocated_to_goals, 2),
        "one_time_free_cash": round(one_time_free_cash, 2),
        "one_time_unallocated": round(one_time_unallocated, 2),
    }
