"""
Mock Bank Provider Implementation (Task 19)
Provides deterministic, zero-cost banking simulation for local development and automated testing.
Generates realistic institutions, accounts, and transaction feeds with stable external IDs.
"""

import datetime
import secrets
from typing import List, Dict, Any, Optional

from services.bank_providers.base import BaseBankProvider
from services.bank_security import generate_state_token

MOCK_INSTITUTIONS = [
    {
        "institution_id": "ins_mock_finrisk",
        "institution_name": "FinRisk Sandbox Bank",
        "logo_url": "https://api.dicebear.com/7.x/identicon/svg?seed=finrisk_bank",
        "supported_features": ["accounts", "transactions", "identity"],
        "is_mock": True,
    },
    {
        "institution_id": "ins_mock_hdfc",
        "institution_name": "HDFC Sandbox Bank",
        "logo_url": "https://api.dicebear.com/7.x/identicon/svg?seed=hdfc_bank",
        "supported_features": ["accounts", "transactions"],
        "is_mock": True,
    },
    {
        "institution_id": "ins_mock_chase",
        "institution_name": "Chase Sandbox Bank",
        "logo_url": "https://api.dicebear.com/7.x/identicon/svg?seed=chase_bank",
        "supported_features": ["accounts", "transactions"],
        "is_mock": True,
    },
    {
        "institution_id": "ins_mock_sbi",
        "institution_name": "State Bank of India (Sandbox)",
        "logo_url": "https://api.dicebear.com/7.x/identicon/svg?seed=sbi_bank",
        "supported_features": ["accounts", "transactions"],
        "is_mock": True,
    },
]


class MockBankProvider(BaseBankProvider):
    """
    In-memory, deterministic bank data provider for sandbox testing and development.
    Requires no paid cloud accounts or external internet access.
    """

    def get_provider_name(self) -> str:
        return "mock"

    def is_configured(self) -> bool:
        return True

    def get_institutions(self) -> List[Dict[str, Any]]:
        return MOCK_INSTITUTIONS

    def initiate_connection(
        self,
        user_id: str,
        institution_id: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        inst_id = institution_id or "ins_mock_finrisk"
        inst_match = next((i for i in MOCK_INSTITUTIONS if i["institution_id"] == inst_id), MOCK_INSTITUTIONS[0])
        state = generate_state_token(user_id)
        mock_auth_code = f"mock_code_{secrets.token_hex(8)}"

        return {
            "provider": "mock",
            "institution_id": inst_match["institution_id"],
            "institution_name": inst_match["institution_name"],
            "state": state,
            "code": mock_auth_code,
            "consent_url": f"{redirect_uri or '/bank-sync'}?state={state}&code={mock_auth_code}",
            "expires_in": 600,
        }

    def exchange_token(self, code: str, state: str) -> Dict[str, Any]:
        # Generate persistent simulated access token
        access_token = f"mock_token_{code[-12:]}"
        return {
            "access_token": access_token,
            "refresh_token": f"mock_refresh_{code[-8:]}",
            "token_type": "Bearer",
            "expires_in": 86400 * 90,  # 90-day simulated consent
            "institution_id": "ins_mock_finrisk",
            "institution_name": "FinRisk Sandbox Bank",
        }

    def get_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """Returns standard checking and savings accounts for the mock connection."""
        return [
            {
                "external_account_id": "mock_acc_chk_101",
                "account_name": "Everyday Checking Account",
                "account_type": "depository",
                "account_subtype": "checking",
                "mask": "4821",
                "currency": "INR",
                "current_balance": 84250.75,
                "available_balance": 82100.00,
            },
            {
                "external_account_id": "mock_acc_sav_102",
                "account_name": "High-Yield Reserve Savings",
                "account_type": "depository",
                "account_subtype": "savings",
                "mask": "8932",
                "currency": "INR",
                "current_balance": 275000.00,
                "available_balance": 275000.00,
            },
        ]

    def get_transactions(
        self,
        access_token: str,
        start_date: datetime.date,
        end_date: datetime.date,
        account_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generates realistic transactions within the requested date window.
        Uses deterministic external IDs keyed on (date, merchant, amount) to verify idempotency.
        """
        txs = []
        today = end_date or datetime.date.today()
        cur_year = today.year
        cur_month = today.month

        # Calculate base dates for current and previous months
        dates_to_generate = []
        # Current month
        dates_to_generate.append((cur_year, cur_month))
        # Previous month
        prev_m = cur_month - 1 if cur_month > 1 else 12
        prev_y = cur_year if cur_month > 1 else cur_year - 1
        dates_to_generate.append((prev_y, prev_m))

        templates = [
            # Regular monthly salary (Income)
            {"day": 1, "desc": "Corporate Salary Credit - Infosys", "amount": 125000.00, "type": "Income", "acc": "mock_acc_chk_101", "payment_method": "Bank Transfer"},
            # Monthly Rent
            {"day": 3, "desc": "House Rent Transfer Apartment 402", "amount": 28000.00, "type": "Expense", "acc": "mock_acc_chk_101", "payment_method": "Bank Transfer"},
            # Monthly Netflix Subscription
            {"day": 12, "desc": "Netflix Subscription Monthly", "amount": 649.00, "type": "Expense", "acc": "mock_acc_chk_101", "payment_method": "Card"},
            # Monthly Spotify Subscription
            {"day": 15, "desc": "Spotify Premium Individual", "amount": 119.00, "type": "Expense", "acc": "mock_acc_chk_101", "payment_method": "Card"},
            # Electricity Bill (slight monthly variance)
            {"day": 18, "desc": "BESCOM Electricity Bill", "amount": 1340.00, "type": "Expense", "acc": "mock_acc_chk_101", "payment_method": "UPI"},
            # Swiggy Food Orders
            {"day": 7, "desc": "Swiggy Order Bangalore", "amount": 540.00, "type": "Expense", "acc": "mock_acc_chk_101", "payment_method": "UPI"},
            {"day": 21, "desc": "Swiggy Order Bangalore", "amount": 620.00, "type": "Expense", "acc": "mock_acc_chk_101", "payment_method": "UPI"},
            # Amazon Shopping
            {"day": 24, "desc": "Amazon India Retail Purchase", "amount": 2199.00, "type": "Expense", "acc": "mock_acc_chk_101", "payment_method": "Card"},
            # Health / Pharmacy
            {"day": 27, "desc": "Apollo Pharmacy Bangalore", "amount": 780.00, "type": "Expense", "acc": "mock_acc_chk_101", "payment_method": "UPI"},
        ]

        for y, m in dates_to_generate:
            for tmpl in templates:
                try:
                    tx_date = datetime.date(y, m, tmpl["day"])
                except ValueError:
                    tx_date = datetime.date(y, m, 28)

                if start_date <= tx_date <= end_date:
                    # Deterministic provider external transaction ID
                    slug = tmpl["desc"].split()[0].lower()
                    ext_id = f"mock_tx_{tx_date.strftime('%Y%m%d')}_{slug}_{int(tmpl['amount'])}"
                    txs.append({
                        "external_id": ext_id,
                        "external_account_id": tmpl["acc"],
                        "description": tmpl["desc"],
                        "amount": tmpl["amount"],
                        "transaction_date": tx_date,
                        "type": tmpl["type"],
                        "payment_method": tmpl["payment_method"],
                    })

        return txs

    def disconnect(self, access_token: str) -> bool:
        return True
