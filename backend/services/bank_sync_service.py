"""
Bank Synchronization Service (Task 19)
Orchestrates account links, transaction fetching, auto-categorization,
deduplication (via external_id and fallback tuple), and ledger ingestion.
"""

import datetime
import re
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from models.bank_connection import BankConnection
from models.bank_account import BankAccount
from models.transaction import Transaction
from services.bank_providers.factory import get_bank_provider
from services.bank_security import encrypt_token, decrypt_token
from services.categorization_service import categorization_engine
from services.recurring_service import scan_user_recurring_payments
from services.audit_service import log_audit_event


def _normalize_desc(desc: Optional[str]) -> str:
    """Normalizes transaction description for fallback tuple deduplication."""
    if not desc:
        return ""
    cleaned = re.sub(r"[-_/\\#,.:;@()]+", " ", desc.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def connect_bank_institution(
    db: Session,
    user_id: str,
    provider_name: str = "mock",
    institution_id: Optional[str] = None,
    auth_code: Optional[str] = None,
    state: Optional[str] = None,
) -> BankConnection:
    """
    Initializes a new bank connection, exchanges credentials, encrypts access tokens,
    persists linked bank accounts, and triggers an initial sync.
    """
    provider = get_bank_provider(provider_name)

    # Initiate or finalize connection
    init_data = provider.initiate_connection(user_id=user_id, institution_id=institution_id)
    inst_id = institution_id or init_data.get("institution_id", "ins_mock_finrisk")
    inst_name = init_data.get("institution_name", "FinRisk Sandbox Bank")

    code = auth_code or init_data.get("code", "mock_code_auto")
    st = state or init_data.get("state", "mock_state_auto")

    token_data = provider.exchange_token(code=code, state=st)
    raw_access_token = token_data.get("access_token", "")
    raw_refresh_token = token_data.get("refresh_token")

    encrypted_access = encrypt_token(raw_access_token)
    encrypted_refresh = encrypt_token(raw_refresh_token) if raw_refresh_token else None

    # Check for existing connection to same institution
    existing_conn = (
        db.query(BankConnection)
        .filter(
            BankConnection.user_id == user_id,
            BankConnection.institution_id == inst_id,
        )
        .first()
    )

    if existing_conn:
        existing_conn.encrypted_access_token = encrypted_access
        existing_conn.encrypted_refresh_token = encrypted_refresh
        existing_conn.status = "connected"
        existing_conn.sync_status = "idle"
        existing_conn.sync_error_message = None
        existing_conn.updated_at = datetime.datetime.utcnow()
        connection = existing_conn
    else:
        connection = BankConnection(
            user_id=user_id,
            provider=provider.get_provider_name(),
            institution_id=inst_id,
            institution_name=inst_name,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            status="connected",
            sync_status="idle",
        )
        db.add(connection)

    db.commit()
    db.refresh(connection)

    # Populate accounts
    accounts_data = provider.get_accounts(raw_access_token)
    for acc in accounts_data:
        existing_acc = (
            db.query(BankAccount)
            .filter(
                BankAccount.connection_id == connection.id,
                BankAccount.external_account_id == acc["external_account_id"],
            )
            .first()
        )
        if existing_acc:
            existing_acc.account_name = acc["account_name"]
            existing_acc.current_balance = acc.get("current_balance")
            existing_acc.available_balance = acc.get("available_balance")
            existing_acc.is_active = True
        else:
            new_acc = BankAccount(
                connection_id=connection.id,
                user_id=user_id,
                external_account_id=acc["external_account_id"],
                account_name=acc["account_name"],
                account_type=acc.get("account_type", "depository"),
                account_subtype=acc.get("account_subtype", "checking"),
                mask=acc.get("mask"),
                currency=acc.get("currency", "INR"),
                current_balance=acc.get("current_balance"),
                available_balance=acc.get("available_balance"),
                is_active=True,
            )
            db.add(new_acc)

    db.commit()
    db.refresh(connection)

    log_audit_event(
        db, user_id, "BANK_CONNECTED",
        f"Connected to {inst_name} via {provider.get_provider_name()}"
    )

    # Trigger initial transaction sync
    sync_connection(db, connection.id, user_id)
    db.refresh(connection)
    return connection


def sync_connection(
    db: Session,
    connection_id: str,
    user_id: str,
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
) -> Dict[str, Any]:
    """
    Synchronizes accounts and transactions for a linked bank connection.
    Guarantees idempotency via external_id and fallback tuple deduplication.
    Runs auto-categorization on all newly ingested transactions.
    """
    connection = (
        db.query(BankConnection)
        .filter(
            BankConnection.id == connection_id,
            BankConnection.user_id == user_id,
        )
        .first()
    )
    if not connection:
        raise ValueError("Bank connection not found or unauthorized.")

    raw_token = decrypt_token(connection.encrypted_access_token)
    if not raw_token:
        connection.status = "error"
        connection.sync_status = "failed"
        connection.sync_error_message = "Authentication tokens missing or corrupted."
        db.commit()
        raise ValueError("Connection tokens could not be decrypted.")

    provider = get_bank_provider(connection.provider)

    try:
        connection.sync_status = "syncing"
        db.commit()

        # 1. Update accounts
        accounts_data = provider.get_accounts(raw_token)
        acc_map: Dict[str, str] = {}  # external_account_id -> db_id
        for acc in accounts_data:
            db_acc = (
                db.query(BankAccount)
                .filter(
                    BankAccount.connection_id == connection.id,
                    BankAccount.external_account_id == acc["external_account_id"],
                )
                .first()
            )
            if db_acc:
                db_acc.account_name = acc["account_name"]
                db_acc.current_balance = acc.get("current_balance")
                db_acc.available_balance = acc.get("available_balance")
                db_acc.is_active = True
                acc_map[acc["external_account_id"]] = db_acc.id
            else:
                new_acc = BankAccount(
                    connection_id=connection.id,
                    user_id=user_id,
                    external_account_id=acc["external_account_id"],
                    account_name=acc["account_name"],
                    account_type=acc.get("account_type", "depository"),
                    account_subtype=acc.get("account_subtype", "checking"),
                    mask=acc.get("mask"),
                    currency=acc.get("currency", "INR"),
                    current_balance=acc.get("current_balance"),
                    available_balance=acc.get("available_balance"),
                    is_active=True,
                )
                db.add(new_acc)
                db.flush()
                acc_map[acc["external_account_id"]] = new_acc.id

        db.commit()

        # 2. Date window: default last 60 days
        today = datetime.date.today()
        from_date = start_date or (today - datetime.timedelta(days=60))
        to_date = end_date or today

        # 3. Fetch transactions
        raw_txs = provider.get_transactions(
            access_token=raw_token,
            start_date=from_date,
            end_date=to_date,
        )

        # 4. Build existing deduplication indices for this user
        existing_ext_ids = set(
            row[0]
            for row in db.query(Transaction.external_id)
            .filter(Transaction.user_id == user_id, Transaction.external_id.isnot(None))
            .all()
        )

        existing_tuples = set(
            (
                row[0],
                round(float(row[1]), 2),
                row[2],
                _normalize_desc(row[3]),
            )
            for row in db.query(
                Transaction.transaction_date,
                Transaction.amount,
                Transaction.type,
                Transaction.description,
            )
            .filter(Transaction.user_id == user_id)
            .all()
        )

        imported_count = 0
        duplicates_skipped = 0

        # 5. Process and insert transactions
        for tx in raw_txs:
            ext_id = tx.get("external_id")
            amount = round(float(tx["amount"]), 2)
            tx_date = tx["transaction_date"]
            tx_type = tx.get("type", "Expense")
            desc = tx.get("description", "")
            norm_desc = _normalize_desc(desc)

            # Deduplication Check 1: Primary provider transaction ID
            if ext_id and ext_id in existing_ext_ids:
                duplicates_skipped += 1
                continue

            # Deduplication Check 2: Fallback date + amount + type + desc tuple
            tuple_key = (tx_date, amount, tx_type, norm_desc)
            if tuple_key in existing_tuples:
                duplicates_skipped += 1
                continue

            # Auto-categorize newly imported transaction
            cat_result = categorization_engine.categorize(
                description=desc,
                tx_type=tx_type,
                amount=amount,
            )

            new_tx = Transaction(
                user_id=user_id,
                type=tx_type,
                category=cat_result["suggested_category"],
                category_confidence=cat_result["confidence"],
                auto_category=cat_result["suggested_category"],
                is_reviewed=False,
                amount=amount,
                description=desc,
                transaction_date=tx_date,
                payment_method=tx.get("payment_method", "Bank Transfer"),
                external_id=ext_id,
                bank_account_id=acc_map.get(tx.get("external_account_id")),
                source="bank_sync",
            )
            db.add(new_tx)

            # Update working deduplication indices
            if ext_id:
                existing_ext_ids.add(ext_id)
            existing_tuples.add(tuple_key)
            imported_count += 1

        db.commit()

        # 6. Trigger Recurring Payment Detector to register new patterns
        if imported_count > 0:
            try:
                scan_user_recurring_payments(db, user_id)
            except Exception:
                pass

        # 7. Update connection status
        connection.last_sync_at = datetime.datetime.utcnow()
        connection.sync_status = "success"
        connection.status = "connected"
        connection.sync_error_message = None
        db.commit()

        log_audit_event(
            db, user_id, "BANK_SYNC_COMPLETED",
            f"Synced {connection.institution_name}: {imported_count} imported, {duplicates_skipped} duplicates skipped."
        )

        return {
            "connection_id": connection.id,
            "status": "success",
            "imported_count": imported_count,
            "duplicates_skipped": duplicates_skipped,
            "accounts_synced": len(accounts_data),
            "synced_at": connection.last_sync_at,
            "message": f"Sync completed successfully. Imported {imported_count} transactions ({duplicates_skipped} duplicates skipped).",
        }

    except Exception as e:
        db.rollback()
        connection.sync_status = "failed"
        connection.sync_error_message = str(e)[:255]
        db.commit()
        raise


def disconnect_bank_connection(db: Session, connection_id: str, user_id: str) -> bool:
    """
    Safely revokes bank connection consent, invalidates tokens, and unlinks accounts.
    Existing transactions imported from this connection are safely retained with bank_account_id = None.
    """
    connection = (
        db.query(BankConnection)
        .filter(
            BankConnection.id == connection_id,
            BankConnection.user_id == user_id,
        )
        .first()
    )
    if not connection:
        return False

    # 1. Inform provider to revoke consent
    raw_token = decrypt_token(connection.encrypted_access_token)
    if raw_token:
        try:
            provider = get_bank_provider(connection.provider)
            provider.disconnect(raw_token)
        except Exception:
            pass

    # 2. Unlink transactions so they are preserved in ledger
    account_ids = [acc.id for acc in connection.accounts]
    if account_ids:
        db.query(Transaction).filter(
            Transaction.bank_account_id.in_(account_ids)
        ).update({"bank_account_id": None}, synchronize_session=False)

    inst_name = connection.institution_name
    db.delete(connection)
    db.commit()

    log_audit_event(
        db, user_id, "BANK_DISCONNECTED",
        f"Disconnected and revoked consent for {inst_name}."
    )
    return True
