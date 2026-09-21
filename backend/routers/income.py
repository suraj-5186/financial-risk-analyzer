from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database.session import get_db
from models.user import User
from models.income_source import IncomeSource
from models.income_allocation import IncomeAllocation
from models.goal import FinancialGoal
from schemas.income_source import IncomeSourceCreate, IncomeSourceUpdate, IncomeSourceResponse
from schemas.income_allocation import IncomeAllocationRequest, IncomeAllocationResponse, IncomeAllocationItemResponse
from services.auth_service import get_current_user
from services.audit_service import log_audit_event
from services.currency_utils import round_currency, is_currency_equal

router = APIRouter(prefix="/api/income-sources", tags=["income"])

def enrich_income_source_response(source: IncomeSource) -> dict:
    """Helper to calculate allocated and unallocated portions for an income source."""
    allocated_to_goals = 0.0
    free_cash = 0.0
    for alloc in source.allocations:
        if alloc.allocation_type == "GOAL":
            allocated_to_goals += alloc.amount
        elif alloc.allocation_type == "FREE_CASH":
            free_cash += alloc.amount

    allocated_total = allocated_to_goals + free_cash
    unallocated_amount = max(0.0, round_currency(source.amount - allocated_total))

    return {
        "id": source.id,
        "user_id": source.user_id,
        "name": source.name,
        "amount": round_currency(source.amount),
        "income_type": source.income_type,
        "frequency": source.frequency,
        "is_recurring": source.is_recurring,
        "next_expected_date": source.next_expected_date,
        "is_active": source.is_active,
        "created_at": source.created_at,
        "updated_at": source.updated_at,
        "allocated_to_goals": round_currency(allocated_to_goals),
        "free_cash": round_currency(free_cash),
        "unallocated_amount": unallocated_amount,
    }


@router.get("", response_model=List[IncomeSourceResponse])
def list_income_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all income sources for the current user with allocation breakdown."""
    sources = db.query(IncomeSource).filter(
        IncomeSource.user_id == current_user.id
    ).order_by(IncomeSource.created_at.desc()).all()

    return [enrich_income_source_response(s) for s in sources]


@router.post("", response_model=IncomeSourceResponse, status_code=status.HTTP_201_CREATED)
def create_income_source(
    source_in: IncomeSourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new income source with normalized income_type handling."""
    # Harmonize income_type, frequency, and is_recurring
    income_type = source_in.income_type
    frequency = source_in.frequency
    if income_type == "one_time":
        is_recurring = False
        frequency = "one_time"
    else:
        income_type = "recurring"
        is_recurring = True
        if frequency not in ["monthly", "weekly"]:
            frequency = "monthly"

    source = IncomeSource(
        user_id=current_user.id,
        name=source_in.name,
        amount=round_currency(source_in.amount),
        income_type=income_type,
        frequency=frequency,
        is_recurring=is_recurring,
        next_expected_date=source_in.next_expected_date,
        is_active=source_in.is_active,
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    log_audit_event(db, current_user.id, "CREATE_INCOME_SOURCE", f"Created {income_type} income source '{source.name}' for ₹{source.amount:,.2f}")
    return enrich_income_source_response(source)


@router.put("/{source_id}", response_model=IncomeSourceResponse)
def update_income_source(
    source_id: int,
    source_in: IncomeSourceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing income source."""
    source = db.query(IncomeSource).filter(
        IncomeSource.id == source_id,
        IncomeSource.user_id == current_user.id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Income source not found")

    # If source has allocations, protect against mutating amount/type to prevent financial inconsistency
    has_allocations = len(source.allocations) > 0
    if has_allocations:
        if source_in.amount is not None and not is_currency_equal(source_in.amount, source.amount):
            raise HTTPException(
                status_code=400,
                detail="Cannot change the amount of an income source that has already been allocated. Financial allocations are immutable."
            )
        if source_in.income_type is not None and source_in.income_type != source.income_type:
            raise HTTPException(
                status_code=400,
                detail="Cannot change the type of an income source that has active allocations."
            )

    update_data = source_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "amount" and value is not None:
            value = round_currency(value)
        setattr(source, field, value)

    # Sync is_recurring if income_type changed
    if "income_type" in update_data:
        source.is_recurring = (source.income_type == "recurring")
        if not source.is_recurring:
            source.frequency = "one_time"

    db.commit()
    db.refresh(source)
    return enrich_income_source_response(source)


@router.delete("/{source_id}")
def delete_income_source(
    source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an income source.
    CRITICAL RULE: Historical financial integrity is strictly preserved.
    Income sources with active allocations cannot be deleted; they must be deactivated.
    """
    source = db.query(IncomeSource).filter(
        IncomeSource.id == source_id,
        IncomeSource.user_id == current_user.id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Income source not found")

    if len(source.allocations) > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete an income source with active allocations to preserve financial history. Set is_active=false to deactivate it instead."
        )

    db.delete(source)
    db.commit()
    log_audit_event(db, current_user.id, "DELETE_INCOME_SOURCE", f"Deleted unallocated income source '{source.name}'")
    return {"message": "Income source deleted successfully"}


@router.post("/{source_id}/allocate", response_model=IncomeAllocationResponse)
def allocate_income_source(
    source_id: int,
    alloc_in: IncomeAllocationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Atomic allocation of a one-time income event across goals and free cash.
    Guarantees:
    - Sum(allocations) + free_cash == source.amount
    - Idempotency & Immutability: Once allocated, cannot be overwritten silently.
    - Zero goal corruption.
    - Atomic execution: all succeed or all fail.
    """
    # 1. Fetch and validate income source
    source = db.query(IncomeSource).filter(
        IncomeSource.id == source_id,
        IncomeSource.user_id == current_user.id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Income source not found")

    if source.income_type != "one_time":
        raise HTTPException(
            status_code=400,
            detail="Only one-time income sources can be allocated to goals and free cash. Recurring income flows into monthly cash flow."
        )

    if not source.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot allocate an inactive income source."
        )

    # 2. Enforce Immutability: cannot re-allocate an already allocated source
    if len(source.allocations) > 0:
        raise HTTPException(
            status_code=400,
            detail="This income source has already been allocated and is immutable. To adjust, an explicit reversal operation is required."
        )

    # 3. Validate goals ownership and existence FIRST (before math) so cross-user
    #    attempts correctly return 404 rather than a sum-mismatch error.
    goal_ids = [a.goal_id for a in alloc_in.allocations]
    goals_by_id = {}
    if goal_ids:
        goals = db.query(FinancialGoal).filter(
            FinancialGoal.id.in_(goal_ids),
            FinancialGoal.user_id == current_user.id
        ).all()
        goals_by_id = {g.id: g for g in goals}

        for g_id in goal_ids:
            if g_id not in goals_by_id:
                raise HTTPException(
                    status_code=404,
                    detail=f"Goal with ID {g_id} not found or does not belong to the current user."
                )

    # 4. Validate math precision: sum(goals) + free_cash == source.amount
    goal_sum = sum(a.amount for a in alloc_in.allocations)
    free_cash = alloc_in.free_cash_amount
    total_requested = goal_sum + free_cash

    if not is_currency_equal(total_requested, source.amount):
        raise HTTPException(
            status_code=400,
            detail=f"Allocation sum mismatch: Total requested ₹{total_requested:,.2f} (Goals: ₹{goal_sum:,.2f} + Free Cash: ₹{free_cash:,.2f}) does not equal income amount ₹{source.amount:,.2f}."
        )

    # 5. Atomic execution within database transaction
    created_allocations = []
    updated_goals_summary = []

    try:
        # A. Apply Goal Allocations
        for item in alloc_in.allocations:
            rounded_amt = round_currency(item.amount)
            goal = goals_by_id[item.goal_id]
            goal.current_amount = round_currency(goal.current_amount + rounded_amt)

            alloc_rec = IncomeAllocation(
                income_source_id=source.id,
                user_id=current_user.id,
                goal_id=goal.id,
                allocation_type="GOAL",
                amount=rounded_amt,
                notes=item.notes or f"Allocation from {source.name}"
            )
            db.add(alloc_rec)
            created_allocations.append((alloc_rec, goal.title))

            updated_goals_summary.append({
                "id": goal.id,
                "title": goal.title,
                "new_current_amount": goal.current_amount,
                "target_amount": goal.target_amount,
                "status": "COMPLETED" if goal.current_amount >= goal.target_amount else "ON_TRACK"
            })

        # B. Apply Free Cash Allocation
        if free_cash > 0:
            free_cash_rounded = round_currency(free_cash)
            free_alloc = IncomeAllocation(
                income_source_id=source.id,
                user_id=current_user.id,
                goal_id=None,
                allocation_type="FREE_CASH",
                amount=free_cash_rounded,
                notes="Uncommitted Free Cash Reserve"
            )
            db.add(free_alloc)
            created_allocations.append((free_alloc, "Free Cash Reserve"))

        db.commit()

        # Refresh created records
        for alloc_rec, _ in created_allocations:
            db.refresh(alloc_rec)

        log_audit_event(
            db,
            current_user.id,
            "INCOME_ALLOCATION",
            f"Allocated ₹{source.amount:,.2f} from '{source.name}' (Goals: ₹{goal_sum:,.2f}, Free Cash: ₹{free_cash:,.2f})"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Atomic allocation transaction failed: {str(e)}"
        )

    # Format response
    response_items = []
    for alloc_rec, title in created_allocations:
        response_items.append(IncomeAllocationItemResponse(
            id=alloc_rec.id,
            income_source_id=alloc_rec.income_source_id,
            goal_id=alloc_rec.goal_id,
            goal_title=title,
            allocation_type=alloc_rec.allocation_type,
            amount=alloc_rec.amount,
            notes=alloc_rec.notes,
            allocated_at=alloc_rec.allocated_at
        ))

    return IncomeAllocationResponse(
        status="success",
        income_source_id=source.id,
        total_amount=round_currency(source.amount),
        allocated_to_goals=round_currency(goal_sum),
        free_cash=round_currency(free_cash),
        allocations=response_items,
        updated_goals=updated_goals_summary
    )
