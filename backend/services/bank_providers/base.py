"""
Base Bank Provider Abstract Interface (Task 19)
Defines operations required for financial data integration.
"""

from abc import ABC, abstractmethod
import datetime
from typing import List, Dict, Any, Optional


class BaseBankProvider(ABC):
    """
    Abstract Base Class for Open Banking / Financial Data Providers.
    All implementations (Mock, Plaid, Account Aggregator) adhere to this contract.
    """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the canonical identifier of the provider (e.g. 'mock', 'plaid')."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the provider has all necessary API credentials configured."""
        pass

    @abstractmethod
    def get_institutions(self) -> List[Dict[str, Any]]:
        """Returns a list of supported or featured financial institutions."""
        pass

    @abstractmethod
    def initiate_connection(
        self,
        user_id: str,
        institution_id: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Initiates the consent / link flow.
        Returns consent parameters, session tokens, or simulated authorization codes.
        """
        pass

    @abstractmethod
    def exchange_token(self, code: str, state: str) -> Dict[str, Any]:
        """
        Exchanges public token/authorization code for persistent access tokens.
        Returns dictionary with access_token, refresh_token (if any), institution_id, institution_name.
        """
        pass

    @abstractmethod
    def get_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Retrieves all linked accounts under the authorized connection.
        Each account contains: external_account_id, name, type, subtype, mask, currency, current_balance, available_balance.
        """
        pass

    @abstractmethod
    def get_transactions(
        self,
        access_token: str,
        start_date: datetime.date,
        end_date: datetime.date,
        account_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves transactions for linked accounts in the specified date range.
        Each transaction contains:
        external_id, external_account_id, amount, date, description, type ('Income'|'Expense'), category_hint.
        """
        pass

    @abstractmethod
    def disconnect(self, access_token: str) -> bool:
        """Revokes provider connection consent and invalidates tokens."""
        pass
