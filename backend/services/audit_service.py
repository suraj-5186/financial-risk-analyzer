import logging
from sqlalchemy.orm import Session
from models.audit import AuditLog

logger = logging.getLogger("audit_service")

def log_audit_event(db: Session, user_id: str | None, action: str, details: str | None = None, ip_address: str | None = None) -> AuditLog:
    """
    Utility helper to log security or operational events into the database.
    """
    try:
        log_entry = AuditLog(
            user_id=user_id,
            action=action.upper(),
            details=details,
            ip_address=ip_address
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        logger.info(f"Audit log recorded: user_id={user_id}, action={action.upper()}")
        return log_entry
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to write audit log: {e}")
        # Return mock or None, do not crash main process
        return None
