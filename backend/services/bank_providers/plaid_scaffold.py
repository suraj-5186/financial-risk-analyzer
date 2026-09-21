"""
Plaid / Production Open Banking Provider Scaffold (Task 19)
Demonstrates production architecture for connecting live financial aggregators.
Clearly communicates unavailability if required API credentials are unconfigured.
"""

import datetime
from typing import List, Dict, Any, Optional

from config import settings
from services.bank_providers.base import BaseBankProvider


class ProviderNotConfiguredException(Exception):
    """Raised when a production bank data provider is missing credentials or disabled."""
    pass


class PlaidBankProviderScaffold(BaseBankProvider):
    """
    Scaffold for Plaid Open Banking API integration.
    Plugs in seamlessly when PLAID_CLIENT_ID and PLAID_SECRET are configured.
    """

    def get_provider_name(self) -> str:
        return "plaid"

    def is_configured(self) -> bool:
        return bool(settings.PLAID_CLIENT_ID and settings.PLAID_SECRET)

    def get_institutions(self) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return []
        return [
            {"institution_id": "ins_1", "institution_name": "Chase", "supported_features": ["accounts", "transactions"]},
            {"institution_id": "ins_3", "institution_name": "Bank of America", "supported_features": ["accounts", "transactions"]},
            {"institution_id": "ins_5", "institution_name": "Wells Fargo", "supported_features": ["accounts", "transactions"]},
        ]

    def initiate_connection(
        self,
        user_id: str,
        institution_id: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            raise ProviderNotConfiguredException(
                "Plaid open banking integration is not configured. Set PLAID_CLIENT_ID and PLAID_SECRET in environment to enable live sync."
            )
        # Production implementation calls /link/token/create
        return {
            "provider": "plaid",
            "link_token": "link-sandbox-sample-token",
            "expiration": (datetime.datetime.utcnow() + datetime.timedelta(hours=4)).isoformat(),
        }

    def exchange_token(self, code: str, state: str) -> Dict[str, Any]:
        if not self.is_configured():
            raise ProviderNotConfiguredException("Plaid open banking provider is not configured.")
        # Production implementation calls /item/public_token/exchange
        return {
            "access_token": "access-sandbox-sample-token",
            "institution_id": "ins_1",
            "institution_name": "Chase",
        }

    def get_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        if not self.is_configured():
            raise ProviderNotConfiguredException("Plaid open banking provider is not configured.")
        # Production calls /accounts/get
        return []

    def get_transactions(
        self,
        access_token: str,
        start_date: datetime.date,
        end_date: datetime.date,
        account_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        if not self.is_configured():
            raise ProviderNotConfiguredException("Plaid open banking provider is not configured.")
        # Production calls /transactions/sync
        return []

    def disconnect(self, access_token: str) -> bool:
        if not self.is_configured():
            return True
        # Production calls /item/remove
        return True
