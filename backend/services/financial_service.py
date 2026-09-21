import datetime
import calendar
from typing import List, Dict, Any, Optional
from models.profile import FinancialProfile
from models.budget import Budget
from models.goal import FinancialGoal
from models.transaction import Transaction
from services.currency_utils import round_currency, is_currency_equal

def calculate_weighted_health_score(profile: FinancialProfile) -> Dict[str, Any]:
    """
    Calculate Financial Health Score out of 100 based on weighted metrics:
    - Savings Rate -> 35%
    - Expense Ratio -> 30%
    - Debt Ratio -> 20%
    - Spending Consistency -> 15%
    """
    # 1. Savings Rate (35 points) - Target: >= 30%
    savings_rate = profile.savings_rate / 100.0
    if savings_rate >= 0.30:
        savings_score = 35.0
    elif savings_rate <= 0:
        savings_score = 0.0
    else:
        savings_score = (savings_rate / 0.30) * 35.0
        
    # 2. Expense Ratio (30 points) - Target: <= 60%
    expense_ratio = 1.0 - savings_rate
    if expense_ratio <= 0.60:
        expense_score = 30.0
    elif expense_ratio >= 1.0:
        expense_score = 0.0
    else:
        expense_score = 30.0 * (1.0 - (expense_ratio - 0.60) / 0.40)
        
    # 3. Debt Ratio (20 points) - Target: <= 20%
    debt_ratio = profile.debt_ratio / 100.0
    if debt_ratio <= 0.20:
        debt_score = 20.0
    elif debt_ratio >= 0.80:
        debt_score = 0.0
    else:
        debt_score = 20.0 * (1.0 - (debt_ratio - 0.20) / 0.60)
        
    # 4. Spending Consistency (15 points) - Target: 100%
    consistency_score = (profile.spending_consistency / 100.0) * 15.0
    
    score = int(savings_score + expense_score + debt_score + consistency_score)
    score = max(0, min(100, score))
    
    # Map to Grades & Status
    if score >= 90:
        grade = "Excellent"
        status_text = "Exceptional financial control"
    elif score >= 75:
        grade = "Good"
        status_text = "You're doing well"
    elif score >= 50:
        grade = "Moderate"
        status_text = "Room for improvement"
    else:
        grade = "Needs Improvement"
        status_text = "Action required"
        
    return {
        "score": score,
        "grade": grade,
        "status_text": status_text,
        "breakdown": {
            "savings": {
                "score": round(savings_score, 1),
                "max": 35,
                "label": "Savings Habit",
                "value": f"{profile.savings_rate}%",
                "status": "Optimal" if savings_score >= 28 else "Moderate" if savings_score >= 15 else "Low"
            },
            "spending": {
                "score": round(expense_score, 1),
                "max": 30,
                "label": "Spending Discipline",
                "value": f"{round((1.0 - savings_rate)*100, 1)}%",
                "status": "Controlled" if expense_score >= 24 else "Moderate" if expense_score >= 12 else "High"
            },
            "debt": {
                "score": round(debt_score, 1),
                "max": 20,
                "label": "Debt Safety",
                "value": f"{profile.debt_ratio}%",
                "status": "Safe" if debt_score >= 16 else "Moderate" if debt_score >= 8 else "Critical"
            },
            "emergency_fund": {
                "score": round(min(15.0, (profile.emergency_fund_months / 6.0) * 15.0), 1),
                "max": 15,
                "label": "Emergency Cushion",
                "value": f"{profile.emergency_fund_months} mo",
                "status": "Protected" if profile.emergency_fund_months >= 3 else "Vulnerable"
            },
            "goal_progress": {
                "score": round(consistency_score, 1),
                "max": 15,
                "label": "Consistency & Goals",
                "value": f"{profile.spending_consistency}%",
                "status": "On Track" if consistency_score >= 10 else "Lagging"
            }
        }
    }

def calculate_safe_to_spend(
    profile: FinancialProfile,
    budgets: List[Budget],
    goals: List[FinancialGoal],
    transactions: List[Transaction],
    income_sources: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    Calculate explainable Safe-to-Spend metrics based on the hierarchy:
    Recurring Income - Essential Obligations (Rent/Bills/EMI) - Mandatory Goal Commitments - Emergency Cushion.
    
    IMPORTANT RULES:
    1. Only active recurring income sources contribute to recurring_monthly_income.
    2. One-time income sources MUST NEVER increase recurring_monthly_income.
    3. Mandatory commitments (fixed bills + urgent/emergency goals) are deducted; optional/long-term goals are exposed separately.
    4. One-time free cash is returned separately as supplemental_free_cash.
    """
    today = datetime.date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_remaining = max(1, days_in_month - today.day + 1)
    
    # 1. Compute Recurring Monthly Income (One-time income strictly excluded)
    supplemental_free_cash = 0.0
    if income_sources:
        active_sources = [s for s in income_sources if s.is_active]
        active_recurring = [s for s in active_sources if getattr(s, "income_type", "recurring") == "recurring"]
        
        monthly_from_sources = sum(
            s.amount for s in active_recurring if s.frequency == "monthly"
        )
        weekly_as_monthly = sum(
            s.amount * 4.33 for s in active_recurring if s.frequency == "weekly"
        )
        
        if (monthly_from_sources + weekly_as_monthly) > 0:
            recurring_monthly_income = round_currency(monthly_from_sources + weekly_as_monthly)
        else:
            recurring_monthly_income = round_currency(profile.monthly_income or 50000.0)
            
        # Collect unallocated or free-cash from one-time sources
        active_one_time = [s for s in active_sources if getattr(s, "income_type", "recurring") == "one_time"]
        for ots in active_one_time:
            allocated_sum = 0.0
            if hasattr(ots, "allocations") and ots.allocations:
                for a in ots.allocations:
                    if getattr(a, "allocation_type", "") == "FREE_CASH":
                        supplemental_free_cash += a.amount
                    allocated_sum += a.amount
            unalloc = max(0.0, ots.amount - allocated_sum)
            supplemental_free_cash += unalloc
    else:
        recurring_monthly_income = round_currency(profile.monthly_income or 50000.0)
        
    supplemental_free_cash = round_currency(supplemental_free_cash)

    # 2. Essential Obligations (Fixed categories in budgets: rent, bills, utilities, emi, loan)
    fixed_categories = {"rent & bills", "rent", "bills", "utilities", "emi", "loan", "education"}
    essential_obligations = 0.0
    for b in budgets:
        if b.category.strip().lower() in fixed_categories:
            essential_obligations += b.monthly_limit
            
    if essential_obligations == 0.0:
        essential_obligations = round_currency(recurring_monthly_income * 0.30)
    else:
        essential_obligations = round_currency(essential_obligations)
        
    # 3. Hierarchy of Goals: Mandatory/Urgent vs Planned/Optional
    mandatory_goal_commitments = 0.0
    planned_goal_commitments = 0.0
    
    for g in goals:
        rem = max(0.0, g.target_amount - g.current_amount)
        if rem <= 0:
            continue
            
        months = max(1, (g.target_date.year - today.year)*12 + (g.target_date.month - today.month))
        required_contribution = rem / months
        
        days_to_target = (g.target_date - today).days
        is_urgent = days_to_target <= 90 or any(k in g.title.lower() for k in ["emergency", "debt", "loan"])
        
        if is_urgent:
            mandatory_goal_commitments += required_contribution
        else:
            planned_goal_commitments += required_contribution
            
    mandatory_goal_commitments = round_currency(mandatory_goal_commitments)
    planned_goal_commitments = round_currency(planned_goal_commitments)
    
    # 4. Emergency Cushion Allocation (10% until 3 months runway established)
    emergency_allocation = round_currency(recurring_monthly_income * 0.10) if profile.emergency_fund_months < 3 else 0.0
    
    # 5. Baseline Monthly Safe Spending Allowance
    monthly_safe_spending = max(
        0.0,
        round_currency(recurring_monthly_income - essential_obligations - mandatory_goal_commitments - emergency_allocation)
    )
    
    # 6. Month-to-date Discretionary/Variable spending
    this_month_expenses = sum(
        t.amount for t in transactions
        if t.type == "Expense" and t.transaction_date.year == today.year and t.transaction_date.month == today.month
    )
    spent_so_far = round_currency(this_month_expenses)
    
    # 7. Remaining Safe Spending & Daily Allowance
    remaining_safe_spending = max(0.0, round_currency(monthly_safe_spending - spent_so_far))
    safe_to_spend_today = max(0.0, round_currency(remaining_safe_spending / days_remaining))
    
    # 8. Human-Readable Transparent Explanation
    explanation = (
        f"Your safe spending today is ₹{safe_to_spend_today:,.0f} based on ₹{recurring_monthly_income:,.0f}/mo "
        f"recurring income, ₹{essential_obligations:,.0f} essential bills, ₹{mandatory_goal_commitments:,.0f} "
        f"urgent goal commitments, and ₹{spent_so_far:,.0f} already spent."
    )
    
    return {
        "safe_to_spend_today": safe_to_spend_today,
        "monthly_safe_spending": monthly_safe_spending,
        "spent_so_far": spent_so_far,
        "remaining_safe_spending": remaining_safe_spending,
        "days_remaining_in_month": days_remaining,
        "fixed_obligations": essential_obligations,
        "essential_obligations": essential_obligations,
        "mandatory_goal_commitments": mandatory_goal_commitments,
        "planned_goal_commitments": planned_goal_commitments,
        "goal_commitments": round_currency(mandatory_goal_commitments + planned_goal_commitments),
        "emergency_allocation": emergency_allocation,
        "monthly_income": recurring_monthly_income,
        "recurring_monthly_income": recurring_monthly_income,
        "supplemental_free_cash": supplemental_free_cash,
        "explanation": explanation
    }

def calculate_goal_protection_status(
    goals: List[FinancialGoal],
    profile: FinancialProfile,
    transactions: List[Transaction]
) -> List[Dict[str, Any]]:
    """
    Evaluate health, shortfall, and timeline risks for each active goal.
    Accounts for extra income allocations that updated current_amount.
    """
    today = datetime.date.today()
    results = []
    
    this_month_income = sum(
        t.amount for t in transactions
        if t.type == "Income" and t.transaction_date.year == today.year and t.transaction_date.month == today.month
    ) or profile.monthly_income or 50000.0
    
    this_month_expense = sum(
        t.amount for t in transactions
        if t.type == "Expense" and t.transaction_date.year == today.year and t.transaction_date.month == today.month
    ) or (this_month_income * (1.0 - profile.savings_rate / 100.0))
    
    available_monthly_savings = max(0.0, this_month_income - this_month_expense)
    
    for g in goals:
        rem_amount = max(0.0, g.target_amount - g.current_amount)
        progress_pct = min(100.0, round((g.current_amount / g.target_amount * 100.0) if g.target_amount > 0 else 100.0, 1))
        
        days_left = (g.target_date - today).days
        months_left = max(1, (g.target_date.year - today.year)*12 + (g.target_date.month - today.month))
        
        required_monthly = round_currency(rem_amount / months_left) if months_left > 0 else rem_amount
        
        # Check if goal received bonus allocations
        allocated_bonus = 0.0
        if hasattr(g, "income_allocations") and g.income_allocations:
            allocated_bonus = sum(a.amount for a in g.income_allocations if getattr(a, "allocation_type", "") == "GOAL")
            
        # Determine status
        if progress_pct >= 100.0 or rem_amount <= 0:
            status = "COMPLETED"
            status_label = "Goal Achieved"
            risk_badge = "COMPLETED"
            shortfall = 0.0
            delay_days = 0
            explanation = "Congratulations! Target amount achieved."
        elif days_left <= 0:
            status = "DELAYED"
            status_label = "Delayed"
            risk_badge = "DELAYED"
            shortfall = rem_amount
            delay_days = abs(days_left) + 30
            explanation = f"Target date passed on {g.target_date.strftime('%d %b %Y')}. ₹{rem_amount:,.0f} still required."
        elif available_monthly_savings >= required_monthly * 0.95:
            status = "ON_TRACK"
            status_label = "On Track"
            risk_badge = "ON TRACK"
            shortfall = 0.0
            delay_days = 0
            explanation = (
                f"Paced to achieve by {g.target_date.strftime('%d %b %Y')} with ₹{required_monthly:,.0f}/mo contribution."
                + (f" (Boosted by ₹{allocated_bonus:,.0f} from bonus allocation)" if allocated_bonus > 0 else "")
            )
        elif available_monthly_savings >= required_monthly * 0.50:
            status = "NEEDS_ATTENTION"
            status_label = "Needs Attention"
            risk_badge = "NEEDS ATTENTION"
            projected_saved = available_monthly_savings * months_left
            shortfall = max(0.0, rem_amount - projected_saved)
            delay_days = int((shortfall / (available_monthly_savings / 30.0))) if available_monthly_savings > 0 else 45
            explanation = f"Current monthly savings (₹{available_monthly_savings:,.0f}) is below required ₹{required_monthly:,.0f}/mo. Projected shortfall: ₹{shortfall:,.0f}."
        else:
            status = "AT_RISK"
            status_label = "At Risk"
            risk_badge = "AT RISK"
            projected_saved = available_monthly_savings * months_left
            shortfall = max(0.0, rem_amount - projected_saved)
            delay_days = int((shortfall / (max(100.0, available_monthly_savings) / 30.0)))
            explanation = f"High risk of missing target date. Need ₹{required_monthly:,.0f}/mo but tracking ₹{available_monthly_savings:,.0f}/mo."
            
        results.append({
            "id": g.id,
            "title": g.title,
            "target_amount": round_currency(g.target_amount),
            "current_amount": round_currency(g.current_amount),
            "target_date": g.target_date.isoformat(),
            "formatted_target_date": g.target_date.strftime("%d %b %Y"),
            "progress_pct": progress_pct,
            "required_monthly_contribution": required_monthly,
            "allocated_bonus": round_currency(allocated_bonus),
            "months_left": months_left,
            "days_left": max(0, days_left),
            "status": status,
            "status_label": status_label,
            "risk_badge": risk_badge,
            "projected_shortfall": round_currency(shortfall),
            "delay_days": delay_days,
            "explanation": explanation
        })
        
    return results

def detect_anomalies(transactions: List[Transaction]) -> List[str]:
    """Detect unusual spending patterns: duplicate payments, sudden spikes, or large transactions."""
    alerts = []
    if not transactions:
        return alerts
        
    expenses = [t for t in transactions if t.type == "Expense"]
    if not expenses:
        return alerts
        
    avg_expense = sum(t.amount for t in expenses) / len(expenses)
    if len(expenses) >= 3:
        for t in expenses:
            if t.amount > 3 * avg_expense and t.amount > 2000:
                alerts.append(
                    f"Unusually large expense: ₹{t.amount:,.0f} for {t.category} on {t.transaction_date} "
                    f"({(t.amount / avg_expense):.1f}x your average)."
                )
                
    seen_transactions = {}
    for t in expenses:
        key = (t.category, t.amount, t.transaction_date)
        if key in seen_transactions:
            alerts.append(
                f"Duplicate payment alert: Multiple charges of ₹{t.amount:,.0f} in {t.category} on {t.transaction_date}."
            )
        else:
            seen_transactions[key] = t
            
    today = datetime.date.today()
    this_month_expenses = [t for t in expenses if t.transaction_date.year == today.year and t.transaction_date.month == today.month]
    prev_month_expenses = [t for t in expenses if t.transaction_date < datetime.date(today.year, today.month, 1)]
    
    if this_month_expenses and prev_month_expenses:
        categories = set(t.category for t in expenses)
        for cat in categories:
            this_cat_total = sum(t.amount for t in this_month_expenses if t.category == cat)
            prev_cat_items = [t for t in prev_month_expenses if t.category == cat]
            if prev_cat_items:
                monthly_totals = {}
                for t in prev_cat_items:
                    mkey = (t.transaction_date.year, t.transaction_date.month)
                    monthly_totals[mkey] = monthly_totals.get(mkey, 0.0) + t.amount
                avg_prev_monthly = sum(monthly_totals.values()) / len(monthly_totals)
                if avg_prev_monthly > 1000 and this_cat_total > 1.4 * avg_prev_monthly:
                    pct = int(((this_cat_total - avg_prev_monthly) / avg_prev_monthly) * 100)
                    alerts.append(
                        f"Spending spike: {cat} is {pct}% higher this month (₹{this_cat_total:,.0f} vs avg ₹{avg_prev_monthly:,.0f})."
                    )
                    
    return alerts

def forecast_expenses_and_savings(transactions: List[Transaction], monthly_income: float) -> Dict[str, float]:
    """Forecast next month's expenses using a simple linear trend, falling back to averages."""
    expenses = [t for t in transactions if t.type == "Expense"]
    if not expenses:
        return {"forecasted_expense": round(monthly_income * 0.70, 2), "forecasted_savings": round(monthly_income * 0.30, 2)}
        
    monthly_totals = {}
    for t in expenses:
        key = (t.transaction_date.year, t.transaction_date.month)
        monthly_totals[key] = monthly_totals.get(key, 0.0) + t.amount
        
    sorted_keys = sorted(monthly_totals.keys())
    totals = [monthly_totals[k] for k in sorted_keys]
    
    if len(totals) < 2:
        forecasted_expense = totals[0] * 1.05 if totals else (monthly_income * 0.70)
    else:
        x = list(range(len(totals)))
        y = totals
        x_mean = sum(x) / len(x)
        y_mean = sum(y) / len(y)
        num = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(len(x)))
        den = sum((x[i] - x_mean) ** 2 for i in range(len(x)))
        slope = num / den if den != 0 else 0.0
        intercept = y_mean - slope * x_mean
        forecasted_expense = max(0.0, slope * len(totals) + intercept)
        
    forecasted_savings = max(0.0, monthly_income - forecasted_expense)
    return {
        "forecasted_expense": round(forecasted_expense, 2),
        "forecasted_savings": round(forecasted_savings, 2)
    }

def calculate_balance_forecast_scenarios(
    transactions: List[Transaction],
    monthly_income: float,
    current_balance: float
) -> Dict[str, Any]:
    """
    Project month-end balance under Expected, High-Spending, and Low-Spending scenarios.
    """
    today = datetime.date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_left = max(1, days_in_month - today.day + 1)
    
    this_month_spent = sum(
        t.amount for t in transactions
        if t.type == "Expense" and t.transaction_date.year == today.year and t.transaction_date.month == today.month
    )
    
    # Calculate daily burn rate
    days_elapsed = max(1, today.day)
    daily_burn = this_month_spent / days_elapsed
    
    projected_additional_expense = daily_burn * days_left
    expected_month_expense = this_month_spent + projected_additional_expense
    
    expected_end_balance = max(0.0, current_balance + (monthly_income - expected_month_expense))
    high_spend_end_balance = max(0.0, current_balance + (monthly_income - (expected_month_expense * 1.20)))
    low_spend_end_balance = current_balance + (monthly_income - (expected_month_expense * 0.85))
    
    # Generate weekly projection trajectory chart data
    chart_points = [
        {"day": f"Day {max(1, today.day - 14)}", "expected": round(current_balance * 0.90, 0), "high_spend": round(current_balance * 0.90, 0), "low_spend": round(current_balance * 0.90, 0)},
        {"day": f"Day {max(1, today.day - 7)}", "expected": round(current_balance * 0.95, 0), "high_spend": round(current_balance * 0.93, 0), "low_spend": round(current_balance * 0.97, 0)},
        {"day": "Today", "expected": round(current_balance, 0), "high_spend": round(current_balance, 0), "low_spend": round(current_balance, 0)},
        {"day": f"Day {min(days_in_month, today.day + 7)}", "expected": round((current_balance + expected_end_balance)/2, 0), "high_spend": round((current_balance + high_spend_end_balance)/2, 0), "low_spend": round((current_balance + low_spend_end_balance)/2, 0)},
        {"day": "Month-End", "expected": round(expected_end_balance, 0), "high_spend": round(high_spend_end_balance, 0), "low_spend": round(low_spend_end_balance, 0)}
    ]
    
    return {
        "projected_month_end_balance": round(expected_end_balance, 0),
        "scenarios": {
            "expected": round(expected_end_balance, 0),
            "high_spending": round(high_spend_end_balance, 0),
            "low_spending": round(low_spend_end_balance, 0)
        },
        "chart_data": chart_points,
        "daily_burn_rate": round(daily_burn, 0)
    }

def generate_structured_risks_and_actions(
    profile: FinancialProfile,
    goals: List[FinancialGoal],
    budgets: List[Budget],
    transactions: List[Transaction],
    anomalies: List[str]
) -> Dict[str, Any]:
    """
    Generate actionable structured financial risks and 'Next Best Actions'.
    """
    risks = []
    actions = []
    
    goal_statuses = calculate_goal_protection_status(goals, profile, transactions)
    
    # 1. Goal Risks
    for g in goal_statuses:
        if g["status"] in ["AT_RISK", "NEEDS_ATTENTION", "DELAYED"]:
            severity = "high" if g["status"] in ["AT_RISK", "DELAYED"] else "medium"
            risks.append({
                "id": f"risk-goal-{g['id']}",
                "severity": severity,
                "category": "Goal Protection",
                "title": f"{g['title']} Goal is {g['status_label']}",
                "explanation": g["explanation"],
                "financial_impact": f"Projected shortfall: ₹{g['projected_shortfall']:,.0f} (Delay ~{g['delay_days']} days)" if g['projected_shortfall'] > 0 else f"Delayed by {g['delay_days']} days",
                "recommended_action": f"Allocate ₹{g['required_monthly_contribution']:,.0f}/mo or reduce discretionary spending."
            })
            
    # 2. Budget Risks
    for b in budgets:
        if b.monthly_limit > 0:
            spent_pct = (b.spent / b.monthly_limit) * 100
            if spent_pct >= 100:
                risks.append({
                    "id": f"risk-budget-{b.id}",
                    "severity": "high",
                    "category": "Overspending",
                    "title": f"Budget Exceeded in {b.category}",
                    "explanation": f"You spent ₹{b.spent:,.0f} against a limit of ₹{b.monthly_limit:,.0f} ({spent_pct:.0f}% used).",
                    "financial_impact": f"₹{(b.spent - b.monthly_limit):,.0f} deficit in this category",
                    "recommended_action": f"Pause non-essential {b.category} expenses for the rest of the month."
                })
            elif spent_pct >= 80:
                risks.append({
                    "id": f"risk-budget-{b.id}",
                    "severity": "medium",
                    "category": "Budget Warning",
                    "title": f"{b.category} Budget Nearing Cap",
                    "explanation": f"You have reached {spent_pct:.0f}% of your monthly limit.",
                    "financial_impact": f"Only ₹{(b.monthly_limit - b.spent):,.0f} remaining",
                    "recommended_action": "Pace your spending to avoid crossing category limits."
                })
                
    # 3. Anomaly Risks
    for i, a in enumerate(anomalies[:2]):
        risks.append({
            "id": f"risk-anomaly-{i}",
            "severity": "medium",
            "category": "Unusual Spending",
            "title": "Unusual Transaction Detected",
            "explanation": a,
            "financial_impact": "Discretionary cash leakage",
            "recommended_action": "Review transaction log to confirm validity."
        })
        
    # 4. Emergency Fund Risk
    if profile.emergency_fund_months < 3:
        risks.append({
            "id": "risk-emergency",
            "severity": "medium",
            "category": "Liquidity Risk",
            "title": "Emergency Reserves Below 3-Month Target",
            "explanation": f"Current liquid runway covers only {profile.emergency_fund_months} months of essential expenses.",
            "financial_impact": "High vulnerability to unexpected expenses or income disruption",
            "recommended_action": "Set up an automatic 10% monthly allocation toward your Emergency Fund."
        })
        
    # Next Best Actions
    # Action A: Smart Allocation for Goal Protection
    at_risk_goals = [g for g in goal_statuses if g["status"] in ["AT_RISK", "NEEDS_ATTENTION"]]
    if at_risk_goals:
        top_g = at_risk_goals[0]
        rec_amt = min(top_g["required_monthly_contribution"], top_g["projected_shortfall"]) if top_g["projected_shortfall"] > 0 else top_g["required_monthly_contribution"]
        actions.append({
            "id": f"act-protect-goal-{top_g['id']}",
            "type": "GOAL_TOPUP",
            "title": f"Defend Your {top_g['title']} Goal",
            "explanation": f"You are currently projected to miss your target date. Adding a contribution of ₹{rec_amt:,.0f} protects your timeline.",
            "estimated_financial_impact": f"Secures completion by {top_g['formatted_target_date']}",
            "recommended_action": f"Top-up ₹{rec_amt:,.0f} to {top_g['title']}",
            "target_id": top_g["id"],
            "suggested_amount": round_currency(rec_amt),
            "badge": "High Priority"
        })
        
    # Action B: Discretionary Spending Optimization
    top_spent_budget = max(budgets, key=lambda b: (b.spent/b.monthly_limit) if b.monthly_limit > 0 else 0) if budgets else None
    if top_spent_budget and top_spent_budget.spent > 0:
        trim_amt = round_currency(top_spent_budget.spent * 0.15)
        actions.append({
            "id": f"act-optimize-budget-{top_spent_budget.id}",
            "type": "BUDGET_ADJUST",
            "title": f"Trim {top_spent_budget.category} Spending",
            "explanation": f"Reducing your {top_spent_budget.category} expenditure by ₹{trim_amt:,.0f} frees up cash directly for essential goals.",
            "estimated_financial_impact": f"Saves ₹{trim_amt:,.0f}/month",
            "recommended_action": f"Reduce {top_spent_budget.category} limit to ₹{round_currency(max(100.0, top_spent_budget.monthly_limit - trim_amt)):,.0f}",
            "target_id": top_spent_budget.id,
            "suggested_amount": round_currency(max(100.0, top_spent_budget.monthly_limit - trim_amt)),
            "badge": "Smart Saving"
        })
        
    # Action C: Emergency Fund Top-up
    if profile.emergency_fund_months < 3:
        suggested_cushion = round_currency((profile.monthly_income or 50000.0) * 0.10)
        actions.append({
            "id": "act-emergency-fund",
            "type": "EMERGENCY_RESERVE",
            "title": "Strengthen Emergency Runway",
            "explanation": f"Allocating ₹{suggested_cushion:,.0f} boosts your liquid safety net toward a safe 3-month buffer.",
            "estimated_financial_impact": "+0.5 months emergency runway",
            "recommended_action": f"Allocate ₹{suggested_cushion:,.0f} to emergency savings",
            "target_id": profile.id,
            "suggested_amount": suggested_cushion,
            "badge": "Financial Safety"
        })
        
    return {
        "risks": risks,
        "actions": actions
    }

def generate_insights_and_recommendations(
    profile: FinancialProfile,
    budgets: List[Budget],
    anomalies: List[str]
) -> Dict[str, List[str]]:
    """Legacy helper for backward compatibility."""
    insights = []
    recommendations = []
    if profile.savings_rate < 15.0:
        insights.append(f"Your savings rate ({profile.savings_rate}%) is below the healthy 20% baseline.")
        recommendations.append(f"Increase monthly savings by ₹{(profile.monthly_income * 0.05):,.0f} to build a safer cushion.")
    elif profile.savings_rate >= 30.0:
        insights.append(f"Your savings rate is high ({profile.savings_rate}%), accelerating your path to financial freedom.")
        recommendations.append("Consider allocating excess savings toward investments (mutual funds or equities).")
    if profile.debt_ratio > 40.0:
        insights.append(f"Debt payments utilize {profile.debt_ratio}% of your income. This creates significant financial vulnerability.")
        recommendations.append("Limit credit card spending immediately and focus on paying down high-interest balances.")
    if profile.emergency_fund_months < 3:
        insights.append(f"Your emergency reserves cover only {profile.emergency_fund_months} months of expenses.")
        recommendations.append("Prioritize emergency fund contributions to secure at least a 3-to-6-month liquid cushion.")
    for budget in budgets:
        if budget.monthly_limit > 0:
            pct = (budget.spent / budget.monthly_limit) * 100
            if pct >= 100:
                insights.append(f"Overspent budget: You exceeded the limit for {budget.category} by ₹{(budget.spent - budget.monthly_limit):,.0f}.")
                recommendations.append(f"Set a strict budget notification alert for {budget.category} and reduce non-essential categories.")
            elif pct >= 80:
                insights.append(f"Budget alert: You used {pct:.0f}% of your category limit for {budget.category}.")
    if not insights:
        insights.append("Your spending behavior is stable and matches target parameters.")
    if not recommendations:
        recommendations.append("Maintain an emergency fund and review monthly subscriptions to identify leakage.")
    return {
        "insights": insights,
        "recommendations": recommendations
    }
