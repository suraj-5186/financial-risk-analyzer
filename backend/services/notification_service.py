import datetime
from sqlalchemy.orm import Session
from models.notification import Notification
from models.user import User
from models.profile import FinancialProfile
from models.budget import Budget
from models.transaction import Transaction

def create_notification_if_not_exists(
    db: Session,
    user_id: str,
    title: str,
    message: str,
    type_val: str
) -> bool:
    """Create a notification in the DB if a similar one hasn't been created in the last 24 hours."""
    yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    
    # Check for recent identical notifications
    exists = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.title == title,
        Notification.created_at >= yesterday
    ).first()
    
    if not exists:
        noti = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type_val
        )
        db.add(noti)
        db.commit()
        return True
    return False

def check_and_trigger_notifications(db: Session, user_id: str):
    """Evaluate financial status, budgets, and goals to trigger user notifications."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return
        
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == user_id).first()
    if not profile:
        return
        
    today = datetime.date.today()
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    
    # 1. Budget Alerts
    budgets = db.query(Budget).filter(Budget.user_id == user_id).all()
    if user.notify_budget_exceeded:
        # Check individual category budgets
        for b in budgets:
            if b.monthly_limit > 0 and b.spent > b.monthly_limit:
                create_notification_if_not_exists(
                    db,
                    user_id,
                    f"Category budget exceeded: {b.category}",
                    f"You have spent {user.currency} {b.spent:,.2f} of your {user.currency} {b.monthly_limit:,.2f} limit for {b.category}.",
                    "budget_exceeded"
                )
        
        # Check global monthly budget
        total_monthly_expense = sum(
            t.amount for t in transactions 
            if t.type == "Expense" and t.transaction_date.year == today.year and t.transaction_date.month == today.month
        )
        if total_monthly_expense > profile.monthly_budget:
            create_notification_if_not_exists(
                db,
                user_id,
                "Global monthly budget exceeded",
                f"Your total expenses this month ({user.currency} {total_monthly_expense:,.2f}) have exceeded your global budget limit of {user.currency} {profile.monthly_budget:,.2f}.",
                "budget_exceeded"
            )
            
    # 2. Savings Below Target Alert
    if user.notify_savings_low:
        if profile.savings_rate < 15.0:
            create_notification_if_not_exists(
                db,
                user_id,
                "Savings rate below target",
                f"Your savings rate is currently {profile.savings_rate:.1f}%, which is below the target 20% threshold.",
                "savings_low"
            )
            
    # 3. High-Risk Status
    if user.notify_high_risk:
        if profile.health_score < 50:
            create_notification_if_not_exists(
                db,
                user_id,
                "Needs Financial Improvement",
                f"Your financial health score is {profile.health_score}/100, which falls into the 'Needs Improvement' zone. Plan budgets carefully.",
                "high_risk"
            )
            
    # 4. Unusual Transaction Detected (Anomalies)
    if user.notify_anomalies and transactions:
        from services.financial_service import detect_anomalies
        anoms = detect_anomalies(transactions)
        for anom in anoms:
            # Clean up message for a shorter title
            title = "Unusual spending detected"
            if "Duplicate" in anom:
                title = "Duplicate payment alert"
            elif "spike" in anom:
                title = "Sudden spending spike"
                
            create_notification_if_not_exists(
                db,
                user_id,
                title,
                anom,
                "anomaly"
            )
