"""
Bank Provider Factory (Task 19)
Resolves and instantiates the active financial data provider based on environment configuration.
"""

from typing import Optional, Dict, Type

from config import settings
from services.bank_providers.base import BaseBankProvider
from services.bank_providers.mock_provider import MockBankProvider
from services.bank_providers.plaid_scaffold import PlaidBankProviderScaffold

_REGISTRY: Dict[str, Type[BaseBankProvider]] = {
    "mock": MockBankProvider,
    "plaid": PlaidBankProviderScaffold,
}

_INSTANCES: Dict[str, BaseBankProvider] = {}


def get_bank_provider(provider_name: Optional[str] = None) -> BaseBankProvider:
    """
    Returns a singleton instance of the requested or default bank data provider.
    Defaults to MockBankProvider for safe local development.
    """
    name = (provider_name or settings.BANK_SYNC_PROVIDER or "mock").lower()
    if name not in _REGISTRY:
        name = "mock"

    if name not in _INSTANCES:
        provider_cls = _REGISTRY[name]
        _INSTANCES[name] = provider_cls()

    return _INSTANCES[name]
