import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from models.profile import FinancialProfile
from schemas.user import UserResponse, UserUpdate, ChangePasswordRequest
from services.auth_service import get_current_user, hash_password, verify_password
from services.financial_service import calculate_weighted_health_score
from services.notification_service import check_and_trigger_notifications

router = APIRouter(prefix="/api/users", tags=["users"])

# Save upload directory
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))

@router.put("/profile", response_model=UserResponse)
def update_profile(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update profile and system settings (theme, currency, notification preferences, income, goals)."""
    # 1. Update User table fields
    if user_in.full_name is not None:
        current_user.full_name = user_in.full_name
    if user_in.currency is not None:
        current_user.currency = user_in.currency
    if user_in.theme is not None:
        current_user.theme = user_in.theme
    if user_in.notify_budget_exceeded is not None:
        current_user.notify_budget_exceeded = user_in.notify_budget_exceeded
    if user_in.notify_savings_low is not None:
        current_user.notify_savings_low = user_in.notify_savings_low
    if user_in.notify_high_risk is not None:
        current_user.notify_high_risk = user_in.notify_high_risk
    if user_in.notify_anomalies is not None:
        current_user.notify_anomalies = user_in.notify_anomalies
        
    # 2. Update Financial Profile fields
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == current_user.id).first()
    if not profile:
        profile = FinancialProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
    if user_in.monthly_income is not None:
        profile.monthly_income = user_in.monthly_income
    if user_in.monthly_budget is not None:
        profile.monthly_budget = user_in.monthly_budget
    if user_in.savings_goal_title is not None:
        profile.savings_goal_title = user_in.savings_goal_title
    if user_in.savings_goal_target is not None:
        profile.savings_goal_target = user_in.savings_goal_target
    if user_in.savings_goal_current is not None:
        profile.savings_goal_current = user_in.savings_goal_current
        
    # Re-calculate health score if any financial metrics changed
    score_res = calculate_weighted_health_score(profile)
    profile.health_score = score_res["score"]
    
    db.commit()
    db.refresh(current_user)
    
    # Run notification rules check
    check_and_trigger_notifications(db, current_user.id)
    
    return current_user

@router.put("/change-password")
def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change account password securely after verifying the old password."""
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )
        
    current_user.hashed_password = hash_password(req.new_password)
    db.commit()
    return {"status": "success", "message": "Password changed successfully"}

import io
from PIL import Image
from config import settings
from services.storage_service import storage_service

SUPPORTED_IMAGE_FORMATS = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
}

@router.post("/profile-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload, validate, and set user avatar with persistent storage."""
    # 1. Validate file existence and read content
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided."
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    # 2. Enforce file size limit (default 5 MB)
    max_bytes = getattr(settings, "AVATAR_MAX_SIZE_BYTES", 5 * 1024 * 1024)
    if len(content) > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of {max_mb} MB."
        )

    # 3. Validate image content and format using PIL
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()
        detected_format = (image.format or "").upper()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or corrupted image file."
        )

    if detected_format not in SUPPORTED_IMAGE_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image format '{detected_format}'. Allowed formats: JPEG, PNG, WebP."
        )

    ext, content_type = SUPPORTED_IMAGE_FORMATS[detected_format]
    unique_filename = f"{uuid.uuid4().hex}{ext}"

    # 4. Save to configured storage backend (Local or S3/R2)
    old_avatar_url = current_user.profile_photo_url
    try:
        new_photo_url = storage_service.save_avatar(
            content=content,
            filename=unique_filename,
            content_type=content_type,
        )
    except ValueError as e:
        # Configuration error (e.g. S3 configured without required credentials)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save avatar to storage backend.",
        )

    # 5. Persist avatar URL in user profile
    current_user.profile_photo_url = new_photo_url
    db.commit()
    db.refresh(current_user)

    # 6. Lifecycle cleanup: delete old avatar object if it was replaced
    if old_avatar_url and old_avatar_url != new_photo_url:
        try:
            storage_service.delete_avatar(old_avatar_url)
        except Exception:
            pass  # Failure to clean up old avatar should not fail the successful upload

    return {
        "status": "success",
        "profile_photo_url": new_photo_url,
        "message": "Avatar updated successfully",
    }


@router.delete("/profile-photo")
def delete_profile_photo(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove user avatar and reset to default."""
    old_avatar_url = current_user.profile_photo_url
    if old_avatar_url:
        current_user.profile_photo_url = None
        db.commit()
        db.refresh(current_user)

        try:
            storage_service.delete_avatar(old_avatar_url)
        except Exception:
            pass

    return {
        "status": "success",
        "profile_photo_url": None,
        "message": "Avatar removed successfully",
    }

