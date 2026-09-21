from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from models.notification import Notification
from schemas.notification import NotificationResponse
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("", response_model=List[NotificationResponse])
def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all notifications for the authenticated user, sorted by date."""
    return db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).all()

@router.put("/{noti_id}/read", response_model=NotificationResponse)
def mark_as_read(
    noti_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a specific notification as read."""
    noti = db.query(Notification).filter(
        Notification.id == noti_id,
        Notification.user_id == current_user.id
    ).first()
    if not noti:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    noti.is_read = True
    db.commit()
    db.refresh(noti)
    return noti

@router.post("/clear")
def clear_all_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete all notifications for the current user."""
    db.query(Notification).filter(Notification.user_id == current_user.id).delete()
    db.commit()
    return {"status": "success", "message": "All notifications cleared"}
