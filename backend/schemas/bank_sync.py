"""
Pydantic Schemas for Bank Synchronization & Open Banking (Task 19)
Enforces token confidentiality: provider secrets are strictly omitted from all client responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class BankAccountResponse(BaseModel):
    id: str
    connection_id: str
    external_account_id: str
    account_name: str
    account_type: str
    account_subtype: Optional[str] = None
    mask: Optional[str] = None
    currency: str = "INR"
    current_balance: Optional[float] = None
    available_balance: Optional[float] = None
    is_active: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BankConnectionResponse(BaseModel):
    id: str
    provider: str
    institution_id: str
    institution_name: str
    status: str
    last_sync_at: Optional[datetime] = None
    sync_status: str
    sync_error_message: Optional[str] = None
    created_at: datetime
    accounts: List[BankAccountResponse] = []

    model_config = ConfigDict(from_attributes=True)


class BankConnectRequest(BaseModel):
    provider: Optional[str] = "mock"
    institution_id: Optional[str] = None
    auth_code: Optional[str] = None
    state: Optional[str] = None


class BankSyncResponse(BaseModel):
    connection_id: str
    status: str
    imported_count: int
    duplicates_skipped: int
    accounts_synced: int
    synced_at: datetime
    message: str


class ProviderStatusResponse(BaseModel):
    provider: str
    is_mock: bool
    is_configured: bool
    supported_institutions: List[Dict[str, Any]]
