from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database.session import get_db
from models.user import User
from models.recurring_payment import RecurringPayment
from schemas.recurring_payment import (
    RecurringPaymentResponse,
    RecurringPaymentUpdate,
    RecurringPaymentSummaryResponse,
    ScanResponse,
)
from services.auth_service import get_current_user
from services.recurring_service import (
    scan_user_recurring_payments,
    get_recurring_summary,
    calculate_normalized_costs,
    calculate_next_payment_date,
)
from services.audit_service import log_audit_event

router = APIRouter(prefix="/api/recurring-payments", tags=["recurring-payments"])


@router.get("", response_model=List[RecurringPaymentResponse])
def list_recurring_payments(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all detected, confirmed, or dismissed recurring payments for the authenticated user."""
    query = db.query(RecurringPayment).filter(RecurringPayment.user_id == current_user.id)
    if status_filter:
        query = query.filter(RecurringPayment.status == status_filter.lower())
    
    return query.order_by(RecurringPayment.estimated_monthly_cost.desc()).all()


@router.post("/scan", response_model=ScanResponse)
def scan_recurring_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Scans the user's transaction ledger to detect periodic payment patterns.
    Updates existing records and adds newly identified recurring payments while
    preserving manual confirmation and dismissal statuses.
    """
    result = scan_user_recurring_payments(db, current_user.id)
    log_audit_event(
        db, current_user.id, "RECURRING_PAYMENTS_SCANNED",
        f"Scanned {result['scanned_transactions_count']} transactions. Detected {result['new_detected_count']} new recurring payments."
    )
    return result


@router.get("/summary", response_model=RecurringPaymentSummaryResponse)
def get_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns aggregated metrics for the user's recurring commitments:
    Total monthly cost, total annual cost, count of active subscriptions,
    and upcoming obligations within the next 30 days.
    """
    return get_recurring_summary(db, current_user.id)


@router.patch("/{payment_id}", response_model=RecurringPaymentResponse)
def update_recurring_payment(
    payment_id: str,
    update_data: RecurringPaymentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Allows the user to confirm, dismiss, or customize notes/frequency for a detected recurring payment.
    Enforces strict user isolation.
    """
    payment = db.query(RecurringPayment).filter(
        RecurringPayment.id == payment_id,
        RecurringPayment.user_id == current_user.id
    ).first()

    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring payment record not found")

    if update_data.status is not None:
        payment.status = update_data.status
    if update_data.notes is not None:
        payment.notes = update_data.notes
    if update_data.frequency is not None:
        payment.frequency = update_data.frequency
        # Recalculate costs and next date if frequency changed
        monthly, annual = calculate_normalized_costs(payment.last_amount, payment.frequency)
        payment.estimated_monthly_cost = monthly
        payment.estimated_annual_cost = annual
        payment.next_estimated_date = calculate_next_payment_date(payment.last_payment_date, payment.frequency)
    if update_data.average_amount is not None and update_data.average_amount > 0:
        payment.average_amount = update_data.average_amount
        payment.last_amount = update_data.average_amount
        monthly, annual = calculate_normalized_costs(payment.last_amount, payment.frequency)
        payment.estimated_monthly_cost = monthly
        payment.estimated_annual_cost = annual

    db.commit()
    db.refresh(payment)

    log_audit_event(
        db, current_user.id, "RECURRING_PAYMENT_UPDATED",
        f"Updated recurring payment {payment.merchant_name} to status '{payment.status}'"
    )
    return payment


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_payment(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a recurring payment record for the authenticated user."""
    payment = db.query(RecurringPayment).filter(
        RecurringPayment.id == payment_id,
        RecurringPayment.user_id == current_user.id
    ).first()

    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring payment record not found")

    db.delete(payment)
    db.commit()
    log_audit_event(
        db, current_user.id, "RECURRING_PAYMENT_DELETED",
        f"Deleted recurring payment {payment.merchant_name}"
    )
    return None
