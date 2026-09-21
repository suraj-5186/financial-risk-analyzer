from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from models.goal import FinancialGoal
from schemas.goal import FinancialGoalCreate, FinancialGoalUpdate, FinancialGoalResponse
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/goals", tags=["goals"])

@router.get("", response_model=List[FinancialGoalResponse])
def get_goals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(FinancialGoal).filter(FinancialGoal.user_id == current_user.id).all()

@router.post("", response_model=FinancialGoalResponse)
def create_goal(
    goal_in: FinancialGoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_goal = FinancialGoal(
        user_id=current_user.id,
        title=goal_in.title,
        target_amount=goal_in.target_amount,
        current_amount=0.0,
        target_date=goal_in.target_date
    )
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal

@router.put("/{goal_id}", response_model=FinancialGoalResponse)
def update_goal(
    goal_id: int,
    goal_in: FinancialGoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    goal = db.query(FinancialGoal).filter(FinancialGoal.id == goal_id, FinancialGoal.user_id == current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
        
    update_data = goal_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(goal, field, value)
        
    db.commit()
    db.refresh(goal)
    return goal
