"""
Bank Synchronization Router (Task 19)
Endpoints for managing financial institution connections, account links, and automated data sync.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.session import get_db
from models.user import User
from models.bank_connection import BankConnection
from models.bank_account import BankAccount
from schemas.bank_sync import (
    BankConnectionResponse,
    BankAccountResponse,
    BankConnectRequest,
    BankSyncResponse,
    ProviderStatusResponse,
)
from services.auth_service import get_current_user
from services.bank_providers.factory import get_bank_provider
from services.bank_sync_service import (
    connect_bank_institution,
    sync_connection,
    disconnect_bank_connection,
)
from config import settings

router = APIRouter(prefix="/api/bank-connections", tags=["Bank Synchronization"])


@router.get("", response_model=List[BankConnectionResponse])
def list_bank_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all linked bank connections for the authenticated user (tokens excluded)."""
    connections = (
        db.query(BankConnection)
        .filter(BankConnection.user_id == current_user.id)
        .order_by(BankConnection.created_at.desc())
        .all()
    )
    return connections


@router.get("/providers", response_model=ProviderStatusResponse)
def get_provider_status(
    current_user: User = Depends(get_current_user),
):
    """Returns active bank sync provider capability and supported institutions."""
    provider = get_bank_provider()
    return {
        "provider": provider.get_provider_name(),
        "is_mock": provider.get_provider_name() == "mock",
        "is_configured": provider.is_configured(),
        "supported_institutions": provider.get_institutions(),
    }


@router.post("/connect", response_model=BankConnectionResponse, status_code=status.HTTP_201_CREATED)
def connect_bank(
    req: BankConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Connects to a financial institution.
    In mock/sandbox mode, establishes connection and performs initial account sync.
    """
    if not settings.BANK_SYNC_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bank synchronization is currently disabled by administrator.",
        )

    try:
        connection = connect_bank_institution(
            db=db,
            user_id=current_user.id,
            provider_name=req.provider or "mock",
            institution_id=req.institution_id,
            auth_code=req.auth_code,
            state=req.state,
        )
        return connection
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect to financial institution: {str(e)}",
        )


@router.get("/{connection_id}/accounts", response_model=List[BankAccountResponse])
def get_connection_accounts(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves all linked accounts for a specific bank connection."""
    connection = (
        db.query(BankConnection)
        .filter(
            BankConnection.id == connection_id,
            BankConnection.user_id == current_user.id,
        )
        .first()
    )
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank connection not found.")

    accounts = (
        db.query(BankAccount)
        .filter(BankAccount.connection_id == connection_id)
        .order_by(BankAccount.account_type, BankAccount.account_name)
        .all()
    )
    return accounts


@router.post("/{connection_id}/sync", response_model=BankSyncResponse)
def trigger_sync(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Triggers on-demand synchronization of transactions and balances.
    Deduplicates incoming records against existing transactions.
    """
    try:
        res = sync_connection(db=db, connection_id=connection_id, user_id=current_user.id)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Synchronization failed: {str(e)}",
        )


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_bank(
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Disconnects a bank link, revoking consent and removing account references.
    Imported transactions are preserved in the user ledger.
    """
    success = disconnect_bank_connection(db=db, connection_id=connection_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank connection not found.")
    return None
