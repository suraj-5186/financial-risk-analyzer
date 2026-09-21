from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from models.audit import AuditLog
from schemas.audit import AuditLogResponse
from services.auth_service import get_current_user
from typing import List

router = APIRouter(prefix="/api/admin/audit-logs", tags=["audit"])

@router.get("", response_model=List[AuditLogResponse])
def get_audit_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve security audit logs. Access is restricted to administrator accounts only.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role access denied. Administrators only."
        )
    
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    return logs
