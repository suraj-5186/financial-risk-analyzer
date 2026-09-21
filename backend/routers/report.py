import io
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from models.profile import FinancialProfile
from models.transaction import Transaction
from models.budget import Budget
from services.auth_service import get_current_user
from services.financial_service import calculate_weighted_health_score, detect_anomalies, generate_insights_and_recommendations
from services.report_service import generate_pdf_report
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from ml.predict import predict_financial_risk

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/download-pdf")
def download_pdf_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate and return a professional PDF financial report."""
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == current_user.id).first()
    if not profile:
        profile = FinancialProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()
    budgets = db.query(Budget).filter(Budget.user_id == current_user.id).all()
    
    # 1. Calculate values
    total_income = sum(t.amount for t in transactions if t.type == "Income")
    total_expense = sum(t.amount for t in transactions if t.type == "Expense")
    savings = total_income - total_expense
    
    # Derived stats for prediction
    inc = total_income if total_income > 0 else profile.monthly_income
    exp = total_expense if total_expense > 0 else (inc * (1.0 - profile.savings_rate/100.0))
    sav = savings if total_income > 0 else (inc * profile.savings_rate/100.0)
    debt = (profile.debt_ratio / 100.0) * inc
    
    # Predict risk
    try:
        prediction = predict_financial_risk({
            "income": inc,
            "expenses": exp,
            "savings": sav,
            "debt": debt,
            "transaction_count": len(transactions)
        })
        risk_level = prediction["risk_level"]
    except Exception:
        risk_level = "Low"
        
    # Health score
    health_res = calculate_weighted_health_score(profile)
    health_score = health_res["score"]
    health_grade = health_res["grade"]
    
    # Anomalies
    anoms = detect_anomalies(transactions)
    
    # AI insights & recommendations
    diagnostics = generate_insights_and_recommendations(profile, budgets, anoms)
    insights = diagnostics["insights"]
    recommendations = diagnostics["recommendations"]
    
    # Currency symbol mapping
    symbol = "₹"
    if current_user.currency == "USD":
        symbol = "$"
    elif current_user.currency == "EUR":
        symbol = "€"
    elif current_user.currency == "GBP":
        symbol = "£"
        
    # Generate PDF in memory buffer
    buffer = io.BytesIO()
    try:
        generate_pdf_report(
            buffer=buffer,
            user_name=current_user.full_name,
            user_email=current_user.email,
            income=total_income,
            expenses=total_expense,
            savings=savings,
            risk_level=risk_level,
            health_score=health_score,
            health_grade=health_grade,
            insights=insights,
            recommendations=recommendations,
            transactions=transactions,
            currency_symbol=symbol
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
        
    buffer.seek(0)
    filename = f"financial_report_{current_user.full_name.lower().replace(' ', '_')}_{date.today().isoformat()}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
