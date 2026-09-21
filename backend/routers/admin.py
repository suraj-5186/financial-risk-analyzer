from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from models.transaction import Transaction
from models.profile import FinancialProfile
from services.auth_service import get_current_user
from sqlalchemy import func

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/dashboard")
def get_admin_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve system-wide dashboard stats for admin users."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
        
    # 1. Total Users
    total_users = db.query(User).count()
    
    # 2. Total Transactions
    total_transactions = db.query(Transaction).count()
    
    # 3. Average Financial Health Score
    avg_health = db.query(func.avg(FinancialProfile.health_score)).scalar() or 0.0
    
    # 4. Most Common Expense Categories
    category_counts = db.query(
        Transaction.category,
        func.count(Transaction.id).label("count")
    ).filter(
        Transaction.type == "Expense"
    ).group_by(
        Transaction.category
    ).order_by(
        func.count(Transaction.id).desc()
    ).all()
    
    formatted_categories = [{"name": cat, "count": count} for cat, count in category_counts]
    
    # 5. Risk Level distribution
    # Let's count risk predictions based on health score ranges (which proxy risk level closely)
    high_risk_count = db.query(FinancialProfile).filter(FinancialProfile.health_score < 50).count()
    medium_risk_count = db.query(FinancialProfile).filter(FinancialProfile.health_score >= 50, FinancialProfile.health_score < 75).count()
    low_risk_count = db.query(FinancialProfile).filter(FinancialProfile.health_score >= 75).count()
    
    # 6. Database stats & system status
    system_status = {
        "status": "Healthy",
        "database_type": "SQLite" if "sqlite" in db.bind.url.drivername else "PostgreSQL",
        "active_connections": 1
    }
    
    return {
        "total_users": total_users,
        "total_transactions": total_transactions,
        "average_health_score": round(float(avg_health), 1),
        "risk_level_distribution": {
            "High": high_risk_count,
            "Medium": medium_risk_count,
            "Low": low_risk_count
        },
        "top_categories": formatted_categories,
        "system": system_status
    }
