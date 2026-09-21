import datetime
import hashlib
import logging
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from config import settings
from database.session import get_db
from models.user import User
from models.profile import FinancialProfile
from models.budget import Budget
from models.goal import FinancialGoal
from models.password_reset import PasswordResetToken
from schemas.user import (
    UserCreate, UserLogin, UserResponse, TokenResponse, TokenRefreshRequest,
    ForgotPasswordRequest, ResetPasswordRequest, GenericMessageResponse
)
from services.auth_service import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, get_current_user
)
from services.audit_service import log_audit_event
from services.email_service import email_service

logger = logging.getLogger("auth")

router = APIRouter(prefix="/api", tags=["authentication"])

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email is already registered."
        )
    
    hashed_pwd = hash_password(user_in.password)
    db_user = User(
        full_name=user_in.full_name,
        email=user_in.email,
        hashed_password=hashed_pwd
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create default financial profile
    default_profile = FinancialProfile(user_id=db_user.id)
    db.add(default_profile)
    
    # Create default budgets
    defaults = [
        ("Food", 10000, 3000),
        ("Rent & Bills", 20000, 20000),
        ("Entertainment", 5000, 1500),
        ("Travel", 5000, 800)
    ]
    for cat, limit, spent in defaults:
        db.add(Budget(user_id=db_user.id, category=cat, monthly_limit=limit, spent=spent))
        
    # Create default goals
    default_goals = [
        FinancialGoal(user_id=db_user.id, title="Emergency Fund", target_amount=100000, current_amount=30000, target_date=datetime.date.today() + datetime.timedelta(days=180)),
        FinancialGoal(user_id=db_user.id, title="Buy Laptop", target_amount=80000, current_amount=15000, target_date=datetime.date.today() + datetime.timedelta(days=90))
    ]
    for goal in default_goals:
        db.add(goal)
        
    db.commit()
    db.refresh(db_user)
    log_audit_event(db, db_user.id, "REGISTER", f"User registered: {db_user.email}")
    return db_user

@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
        
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email, "v": user.token_version or 1})
    log_audit_event(db, user.id, "LOGIN", "User logged in successfully")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=TokenResponse)
def refresh(token_in: TokenRefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(token_in.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
        
    email: str = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Invalidate refresh token if password was reset after this token was issued
    token_v = payload.get("v")
    if token_v is not None and user.token_version and token_v != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired due to recent password reset. Please log in again."
        )

    if user.password_changed_at and payload.get("iat"):
        token_iat = datetime.datetime.fromtimestamp(payload["iat"], tz=datetime.timezone.utc)
        pwd_changed = user.password_changed_at.replace(tzinfo=datetime.timezone.utc) if user.password_changed_at.tzinfo is None else user.password_changed_at
        if token_iat < pwd_changed:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired due to recent password reset. Please log in again."
            )
        
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email, "v": user.token_version or 1})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserResponse)
@router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"status": "success", "message": "Logged out successfully"}

@router.post("/auth/forgot-password", response_model=GenericMessageResponse)
@router.post("/forgot-password", response_model=GenericMessageResponse, include_in_schema=False)
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Request a password reset link.
    Returns the same generic success response whether or not the account exists
    to prevent email enumeration.
    """
    clean_email = request.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == clean_email).first()

    if user:
        # Rate-limiting / cooldown check: limit to 1 request every 60 seconds per user
        cooldown_window = datetime.datetime.utcnow() - datetime.timedelta(seconds=60)
        recent_request = db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.created_at >= cooldown_window
        ).first()

        if not recent_request:
            # Revoke all previous active/unused tokens for this user
            db.query(PasswordResetToken).filter(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.is_used == False,
                PasswordResetToken.is_revoked == False
            ).update({"is_revoked": True})

            # Generate a cryptographically secure, unpredictable reset token
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(
                minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
            )

            # Store only the token hash in the database
            reset_record = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
                is_used=False,
                is_revoked=False
            )
            db.add(reset_record)
            db.commit()

            log_audit_event(db, user.id, "PASSWORD_RESET_REQUEST", "Password reset requested")

            # Dispatch email through email service safely
            try:
                email_service.send_password_reset_email(
                    to_email=user.email,
                    reset_token=raw_token,
                    user_name=user.full_name
                )
            except Exception as e:
                logger.error("Failed to send reset email: %s", type(e).__name__)

    # Always return generic success message to prevent user enumeration
    return {
        "status": "success",
        "message": "If that email address is registered, a password reset link has been sent."
    }

@router.get("/auth/verify-reset-token")
@router.get("/verify-reset-token", include_in_schema=False)
def verify_reset_token(token: str, db: Session = Depends(get_db)):
    """
    Validate whether a password reset token is active and usable.
    Used by the frontend to display accurate feedback upon opening the reset link.
    """
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token is missing or empty."
        )

    submitted_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
    record = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == submitted_hash).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unrecognized password reset link."
        )

    if record.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has already been used."
        )

    if record.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has been superseded by a newer request."
        )

    if datetime.datetime.utcnow() > record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has expired. Please request a new one."
        )

    return {"status": "valid", "message": "Token is valid and active."}

@router.post("/auth/reset-password", response_model=GenericMessageResponse)
@router.post("/reset-password", response_model=GenericMessageResponse, include_in_schema=False)
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Consume a password reset token and update the user's password.
    Ensures the token cannot be reused and updates password_changed_at.
    """
    if not request.token or not request.token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token is required."
        )

    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long."
        )

    submitted_hash = hashlib.sha256(request.token.strip().encode("utf-8")).hexdigest()

    record = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == submitted_hash).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unrecognized password reset token."
        )

    if record.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has already been used."
        )

    if record.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has been revoked. Please request a new one."
        )

    if datetime.datetime.utcnow() > record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has expired. Please request a new one."
        )

    user = db.query(User).filter(User.id == record.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Associated user account was not found."
        )

    # Update password using existing bcrypt hashing
    user.hashed_password = hash_password(request.new_password)
    user.password_changed_at = datetime.datetime.utcnow()
    user.token_version = (user.token_version or 1) + 1

    # Mark this token consumed
    record.is_used = True
    record.is_revoked = True

    # Invalidate any other active reset tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.id != record.id
    ).update({"is_revoked": True})

    log_audit_event(db, user.id, "PASSWORD_RESET_SUCCESS", "Password reset successfully completed")
    db.commit()

    return {
        "status": "success",
        "message": "Password has been successfully reset. You may now sign in with your new password."
    }
