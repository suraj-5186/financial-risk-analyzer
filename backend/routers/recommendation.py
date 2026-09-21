import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from models.goal import FinancialGoal
from models.budget import Budget
from models.profile import FinancialProfile
from models.recommendation import Recommendation
from services.auth_service import get_current_user
from services.audit_service import log_audit_event
from services.currency_utils import round_currency

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

@router.post("/{rec_id}/apply")
def apply_recommendation(
    rec_id: str,
    payload: dict = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes a real backend financial operation for an action.
    Strictly verifies user ownership of all targeted entities.
    """
    payload = payload or {}
    rec_type = payload.get("type")
    target_id = payload.get("target_id")
    suggested_amount = payload.get("suggested_amount")

    # Lock or fetch existing recommendation record (row-level locking where supported)
    # Check if this recommendation has already been applied by this user
    rec_query = db.query(Recommendation).filter(
        Recommendation.user_id == current_user.id,
        (Recommendation.id == rec_id) | (Recommendation.id == f"{current_user.id}_{rec_id}")
    )
    if db.bind.dialect.name != "sqlite":
        rec_query = rec_query.with_for_update()
    rec = rec_query.first()

    if rec and rec.is_applied:
        raise HTTPException(
            status_code=400,
            detail="Recommendation has already been applied."
        )

    response_payload = {}
    audit_msg = None
    now = datetime.datetime.utcnow()

    try:
        # 1. Goal Top-up / Protection Action
        if rec_id.startswith("act-protect-goal") or rec_type == "GOAL_TOPUP":
            goal_id = target_id or (int(rec_id.split("-")[-1]) if rec_id.split("-")[-1].isdigit() else None)
            if not goal_id:
                raise HTTPException(status_code=400, detail="Invalid goal target for recommendation.")
                
            goal_query = db.query(FinancialGoal).filter(
                FinancialGoal.id == goal_id,
                FinancialGoal.user_id == current_user.id
            )
            if db.bind.dialect.name != "sqlite":
                goal_query = goal_query.with_for_update()
            goal = goal_query.first()
            if not goal:
                raise HTTPException(status_code=404, detail="Goal not found or unauthorized.")
                
            amt = round_currency(suggested_amount or 1000.0)
            goal.current_amount = round_currency(goal.current_amount + amt)
            
            audit_msg = f"Applied goal top-up of ₹{amt:,.2f} to '{goal.title}'"
            response_payload = {
                "status": "applied",
                "is_applied": True,
                "message": f"Successfully contributed ₹{amt:,.2f} to '{goal.title}'.",
                "action_id": rec_id,
                "updated_entity": {"goal_id": goal.id, "new_amount": goal.current_amount}
            }

        # 2. Budget Optimization Action
        elif rec_id.startswith("act-optimize-budget") or rec_type == "BUDGET_ADJUST":
            budget_id = target_id or (int(rec_id.split("-")[-1]) if rec_id.split("-")[-1].isdigit() else None)
            if not budget_id:
                raise HTTPException(status_code=400, detail="Invalid budget target for recommendation.")
                
            budget_query = db.query(Budget).filter(
                Budget.id == budget_id,
                Budget.user_id == current_user.id
            )
            if db.bind.dialect.name != "sqlite":
                budget_query = budget_query.with_for_update()
            budget = budget_query.first()
            if not budget:
                raise HTTPException(status_code=404, detail="Budget not found or unauthorized.")
                
            new_limit = round_currency(suggested_amount or max(100.0, budget.monthly_limit * 0.85))
            budget.monthly_limit = new_limit
            
            audit_msg = f"Adjusted '{budget.category}' budget limit to ₹{new_limit:,.2f}"
            response_payload = {
                "status": "applied",
                "is_applied": True,
                "message": f"Updated '{budget.category}' monthly budget limit to ₹{new_limit:,.2f}.",
                "action_id": rec_id,
                "updated_entity": {"budget_id": budget.id, "new_limit": budget.monthly_limit}
            }

        # 3. Emergency Reserve Action
        elif rec_id == "act-emergency-fund" or rec_type == "EMERGENCY_RESERVE":
            profile_query = db.query(FinancialProfile).filter(FinancialProfile.user_id == current_user.id)
            if db.bind.dialect.name != "sqlite":
                profile_query = profile_query.with_for_update()
            profile = profile_query.first()
            if not profile:
                raise HTTPException(status_code=404, detail="Financial profile not found.")
                
            # Verify that if target_id is provided, it belongs to the authenticated user's profile
            if target_id and str(target_id) != str(profile.id):
                raise HTTPException(status_code=403, detail="Unauthorized target profile for emergency reserve action.")

            # Verify whether an emergency fund recommendation is valid/eligible for this user
            persisted_rec = rec if rec and not rec.is_dismissed else None
            is_server_rule_eligible = profile.emergency_fund_months < 3
            is_dismissed = rec.is_dismissed if rec else False

            if not persisted_rec and (not is_server_rule_eligible or is_dismissed):
                raise HTTPException(
                    status_code=400,
                    detail="Emergency reserve recommendation is not active or authorized for this profile."
                )

            profile.emergency_fund_months = min(12, profile.emergency_fund_months + 1)
            
            audit_msg = "Expanded emergency runway target by 1 month"
            response_payload = {
                "status": "applied",
                "is_applied": True,
                "message": "Expanded emergency reserve cushion target.",
                "action_id": rec_id,
                "updated_entity": {"profile_id": profile.id, "emergency_fund_months": profile.emergency_fund_months}
            }

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported action type for recommendation '{rec_id}'."
            )

        # Persist the is_applied status and applied_at timestamp in the SAME transaction
        if rec:
            rec.is_applied = True
            rec.applied_at = now
        else:
            existing_any = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
            record_id = rec_id if not existing_any else f"{current_user.id}_{rec_id}"
            new_rec = Recommendation(
                id=record_id,
                user_id=current_user.id,
                title=payload.get("title") or f"Action: {rec_id}",
                description=payload.get("explanation") or "Executed automated recommendation",
                category=payload.get("category") or ("Savings" if "goal" in rec_id or "emergency" in rec_id else "Budget"),
                priority="High",
                is_applied=True,
                applied_at=now,
                action_type=rec_type or ("GOAL_TOPUP" if "goal" in rec_id else "BUDGET_ADJUST" if "budget" in rec_id else "EMERGENCY_RESERVE"),
            )
            db.add(new_rec)

        db.commit()

        # Log audit event AFTER transaction commits safely
        if audit_msg:
            log_audit_event(db, current_user.id, "APPLY_RECOMMENDATION", audit_msg)

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Atomic application failed: {str(e)}"
        )

    return response_payload

@router.post("/{rec_id}/dismiss")
def dismiss_recommendation(
    rec_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dismiss a recommendation so it does not reappear for the current user.
    """
    rec = db.query(Recommendation).filter(
        Recommendation.user_id == current_user.id,
        (Recommendation.id == rec_id) | (Recommendation.id == f"{current_user.id}_{rec_id}")
    ).first()
    if rec:
        rec.is_dismissed = True
        rec.is_read = True
        db.commit()
        
    log_audit_event(db, current_user.id, "DISMISS_RECOMMENDATION", f"Dismissed recommendation '{rec_id}'")
    return {"status": "dismissed", "action_id": rec_id}
