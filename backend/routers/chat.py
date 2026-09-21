from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from models.chat import ChatHistory
from models.profile import FinancialProfile
from models.transaction import Transaction
from models.budget import Budget
from models.goal import FinancialGoal
from schemas.chat import ChatMessageCreate, ChatHistoryResponse
from services.auth_service import get_current_user
from services.ai_service import ai_service
from services.financial_service import detect_anomalies
from typing import List

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("", response_model=ChatHistoryResponse)
def send_chat_message(
    chat_in: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message to the AI Chatbot and receive a reply.
    """
    # 1. Fetch user financials to build high quality context
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == current_user.id).first()
    if not profile:
        profile = FinancialProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()
    budgets = db.query(Budget).filter(Budget.user_id == current_user.id).all()
    goals = db.query(FinancialGoal).filter(FinancialGoal.user_id == current_user.id).all()
    
    total_income = sum(t.amount for t in transactions if t.type == "Income")
    total_expense = sum(t.amount for t in transactions if t.type == "Expense")
    savings = total_income - total_expense
    
    anomalies = detect_anomalies(transactions)
    anomalies_summary = anomalies[:5]

    # 2. Build summary payload
    financial_data = {
        "income": total_income if total_income > 0 else profile.monthly_income,
        "expenses": total_expense if total_expense > 0 else (profile.monthly_income * (1.0 - profile.savings_rate/100.0)),
        "savings": savings if total_income > 0 else (profile.monthly_income * profile.savings_rate/100.0),
        "savings_rate": profile.savings_rate,
        "debt_ratio": profile.debt_ratio,
        "health_score": profile.health_score,
        "risk_level": getattr(profile, "risk_level", "Medium"), # Fallback risk level
        "budgets": [f"{b.category}: {b.monthly_limit} limit" for b in budgets],
        "goals": [f"{g.title}: target {g.target_amount}, current {g.current_amount}" for g in goals],
        "anomalies": anomalies_summary
    }

    # 3. Retrieve conversation history
    session_id = chat_in.session_id or "default"
    history_records = db.query(ChatHistory).filter(
        ChatHistory.user_id == current_user.id,
        ChatHistory.session_id == session_id
    ).order_by(ChatHistory.created_at.asc()).all()

    history_list = [{"sender": h.sender, "message": h.message} for h in history_records]

    # 4. Generate AI Advice
    ai_response = ai_service.generate_chat_response(financial_data, history_list, chat_in.message)

    # 5. Persist User Message
    user_record = ChatHistory(
        user_id=current_user.id,
        session_id=session_id,
        sender="user",
        message=chat_in.message
    )
    db.add(user_record)

    # 6. Persist Assistant Reply
    assistant_record = ChatHistory(
        user_id=current_user.id,
        session_id=session_id,
        sender="assistant",
        message=ai_response
    )
    db.add(assistant_record)
    
    db.commit()
    db.refresh(assistant_record)

    return assistant_record

@router.get("/history", response_model=List[ChatHistoryResponse])
def get_chat_history(
    session_id: str = "default",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve message history for the current user's session.
    """
    history_records = db.query(ChatHistory).filter(
        ChatHistory.user_id == current_user.id,
        ChatHistory.session_id == session_id
    ).order_by(ChatHistory.created_at.asc()).all()
    return history_records
