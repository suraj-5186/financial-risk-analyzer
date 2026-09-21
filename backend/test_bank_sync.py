"""
Unit and Integration Tests for Open Banking Integration & Bank Sync Foundation (Task 19)

Covers:
- Token encryption at rest (Fernet) & CSRF state verification
- Mock bank provider account & transaction generation
- Provider status & capability discovery
- Connection establishment & linked account discovery
- Token secrecy in client API responses (zero token leakage)
- Idempotent transaction sync & deduplication (external_id & fallback tuple)
- Auto-categorization integration on synced transactions
- User-edited category preservation across repeated syncs
- Safe disconnect & consent revocation preserving ledger history
- Authentication & cross-user tenant data isolation
"""

import os
import sys
import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

TEST_DB_FILE = os.path.join(backend_dir, "test_bank_sync.db")
if os.path.exists(TEST_DB_FILE):
    try:
        os.remove(TEST_DB_FILE)
    except OSError:
        pass

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE}"

from main import app
from models.base import Base
from database.session import get_db
from models.user import User
from models.transaction import Transaction
from models.bank_connection import BankConnection
from models.bank_account import BankAccount
from services.auth_service import create_access_token, hash_password
from database.migrations import run_migrations
from services.bank_security import (
    encrypt_token,
    decrypt_token,
    generate_state_token,
    verify_state_token,
)
from services.bank_providers.factory import get_bank_provider
from services.bank_sync_service import (
    connect_bank_institution,
    sync_connection,
    disconnect_bank_connection,
)

# Setup isolated test DB
engine = create_engine(f"sqlite:///{TEST_DB_FILE}", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)
run_migrations()
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True, scope="module")
def setup_db_module():
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


@pytest.fixture
def user_alice():
    db = TestingSessionLocal()
    user = db.query(User).filter_by(email="bank_alice@example.com").first()
    if not user:
        user = User(
            email="bank_alice@example.com",
            hashed_password=hash_password("PasswordAlice123!"),
            full_name="Alice Sterling",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    u_id = user.id
    db.close()
    token = create_access_token({"sub": "bank_alice@example.com", "user_id": u_id})
    return {"id": u_id, "email": "bank_alice@example.com", "token": token}


@pytest.fixture
def user_bob():
    db = TestingSessionLocal()
    user = db.query(User).filter_by(email="bank_bob@example.com").first()
    if not user:
        user = User(
            email="bank_bob@example.com",
            hashed_password=hash_password("PasswordBob456!"),
            full_name="Bob Vance",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    u_id = user.id
    db.close()
    token = create_access_token({"sub": "bank_bob@example.com", "user_id": u_id})
    return {"id": u_id, "email": "bank_bob@example.com", "token": token}


# ==============================================================================
# 1. Security & Token Cryptography Tests
# ==============================================================================

def test_token_encryption_and_decryption():
    """Verify provider tokens are encrypted at rest and decrypt cleanly."""
    raw_token = "access-sandbox-99824-token-secret"
    encrypted = encrypt_token(raw_token)
    assert encrypted != raw_token
    assert len(encrypted) > 20

    decrypted = decrypt_token(encrypted)
    assert decrypted == raw_token

    # Empty string handling
    assert encrypt_token("") == ""
    assert decrypt_token("") == ""
    assert decrypt_token("invalid-garbage-ciphertext") == ""


def test_csrf_state_token_verification():
    """Verify anti-CSRF state tokens protect OAuth link handshakes."""
    user_id = "test-user-123"
    state = generate_state_token(user_id)
    assert verify_state_token(state, user_id)
    assert not verify_state_token(state, "wrong-user-456")
    assert not verify_state_token("tampered-state-token", user_id)


# ==============================================================================
# 2. Provider Abstraction & Capability Tests
# ==============================================================================

def test_provider_status_api(user_alice):
    """Verify provider status endpoint returns capability discovery without exposing secrets."""
    resp = client.get(
        "/api/bank-connections/providers",
        headers={"Authorization": f"Bearer {user_alice['token']}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "mock"
    assert data["is_mock"] is True
    assert data["is_configured"] is True
    assert len(data["supported_institutions"]) >= 2
    inst_names = [i["institution_name"] for i in data["supported_institutions"]]
    assert any("Sandbox" in name for name in inst_names)


def test_mock_provider_account_and_transaction_contract():
    """Verify MockBankProvider satisfies the BaseBankProvider contract."""
    provider = get_bank_provider("mock")
    assert provider.get_provider_name() == "mock"
    assert provider.is_configured() is True

    init_res = provider.initiate_connection(user_id="u1")
    assert "code" in init_res
    assert "state" in init_res

    token_res = provider.exchange_token(code=init_res["code"], state=init_res["state"])
    assert "access_token" in token_res

    accounts = provider.get_accounts(token_res["access_token"])
    assert len(accounts) >= 2
    assert "external_account_id" in accounts[0]
    assert "mask" in accounts[0]

    today = datetime.date.today()
    start_d = today - datetime.timedelta(days=30)
    txs = provider.get_transactions(token_res["access_token"], start_d, today)
    assert len(txs) > 0
    assert "external_id" in txs[0]
    assert "amount" in txs[0]


# ==============================================================================
# 3. Connection, Token Secrecy, and Account Discovery
# ==============================================================================

def test_connect_bank_and_token_secrecy(user_alice):
    """Verify connecting a bank establishes accounts and NEVER returns provider tokens in API."""
    resp = client.post(
        "/api/bank-connections/connect",
        json={"provider": "mock", "institution_id": "ins_mock_finrisk"},
        headers={"Authorization": f"Bearer {user_alice['token']}"}
    )
    assert resp.status_code == 201
    data = resp.json()
    conn_id = data["id"]
    assert data["institution_name"] == "FinRisk Sandbox Bank"
    assert data["status"] == "connected"
    assert len(data["accounts"]) >= 2

    # SECURITY CHECK: Verify provider tokens/secrets are NOT returned in JSON
    assert "encrypted_access_token" not in data
    assert "access_token" not in data
    assert "encrypted_refresh_token" not in data
    assert "refresh_token" not in data

    # Verify accounts endpoint
    acc_resp = client.get(
        f"/api/bank-connections/{conn_id}/accounts",
        headers={"Authorization": f"Bearer {user_alice['token']}"}
    )
    assert acc_resp.status_code == 200
    accounts = acc_resp.json()
    assert len(accounts) >= 2
    for acc in accounts:
        assert "mask" in acc
        assert acc["currency"] == "INR"
        assert acc["current_balance"] is not None


# ==============================================================================
# 4. Sync Pipeline, Auto-Categorization & Idempotency
# ==============================================================================

def test_sync_pipeline_and_idempotency(user_alice):
    """Verify transactions are imported, auto-categorized, and repeated syncs prevent duplicates."""
    # List connections to get Alice's connection ID
    conns_resp = client.get(
        "/api/bank-connections",
        headers={"Authorization": f"Bearer {user_alice['token']}"}
    )
    assert conns_resp.status_code == 200
    conns = conns_resp.json()
    assert len(conns) >= 1
    conn_id = conns[0]["id"]

    db = TestingSessionLocal()
    initial_tx_count = db.query(Transaction).filter_by(user_id=user_alice["id"]).count()
    assert initial_tx_count > 0  # Seeded on initial connect
    db.close()

    # 1. Trigger Manual Sync
    sync_resp1 = client.post(
        f"/api/bank-connections/{conn_id}/sync",
        headers={"Authorization": f"Bearer {user_alice['token']}"}
    )
    assert sync_resp1.status_code == 200
    result1 = sync_resp1.json()
    assert result1["status"] == "success"
    # Because initial sync already ingested the mock transactions, duplicates must be skipped!
    assert result1["imported_count"] == 0
    assert result1["duplicates_skipped"] >= 5

    # 2. Verify imported transactions have source, external_id, and auto-categories
    db = TestingSessionLocal()
    synced_txs = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_alice["id"], Transaction.source == "bank_sync")
        .all()
    )
    assert len(synced_txs) > 0
    for tx in synced_txs:
        assert tx.external_id is not None
        assert tx.external_id.startswith("mock_tx_")
        assert tx.category is not None
        assert tx.category_confidence is not None
        assert tx.source == "bank_sync"
    db.close()

    # 3. Trigger Second Sync (STRICT IDEMPOTENCY CHECK)
    sync_resp2 = client.post(
        f"/api/bank-connections/{conn_id}/sync",
        headers={"Authorization": f"Bearer {user_alice['token']}"}
    )
    assert sync_resp2.status_code == 200
    result2 = sync_resp2.json()
    assert result2["imported_count"] == 0
    assert result2["duplicates_skipped"] >= 5

    # Verify ledger row count remained unchanged
    db = TestingSessionLocal()
    final_tx_count = db.query(Transaction).filter_by(user_id=user_alice["id"]).count()
    assert final_tx_count == initial_tx_count
    db.close()


def test_fallback_deduplication_without_external_id(user_alice):
    """Verify fallback tuple (date, amount, type, description) prevents duplicates when external_id is absent."""
    db = TestingSessionLocal()
    u_id = user_alice["id"]

    # Insert a manual transaction without external_id
    manual_tx = Transaction(
        user_id=u_id,
        description="Corporate Salary Credit - Infosys",
        amount=125000.00,
        type="Income",
        category="Salary",
        transaction_date=datetime.date(datetime.date.today().year, datetime.date.today().month, 1),
        payment_method="Bank Transfer",
        external_id=None,
        source="manual",
    )
    db.add(manual_tx)
    db.commit()

    conn = db.query(BankConnection).filter_by(user_id=u_id).first()
    conn_id = conn.id
    db.close()

    # Trigger sync
    sync_res = client.post(
        f"/api/bank-connections/{conn_id}/sync",
        headers={"Authorization": f"Bearer {user_alice['token']}"}
    )
    assert sync_res.status_code == 200
    # The duplicate salary row should be skipped by the fallback deduplicator
    assert sync_res.json()["imported_count"] == 0


def test_user_edited_category_preservation_across_syncs(user_alice):
    """Verify user manual category edits on bank-synced transactions are not overwritten by subsequent syncs."""
    db = TestingSessionLocal()
    u_id = user_alice["id"]
    tx = (
        db.query(Transaction)
        .filter(Transaction.user_id == u_id, Transaction.source == "bank_sync")
        .first()
    )
    assert tx is not None
    tx_id = tx.id

    # User manually overrides category to "Custom Category"
    tx.category = "Custom Category"
    tx.is_reviewed = True
    db.commit()

    conn = db.query(BankConnection).filter_by(user_id=u_id).first()
    conn_id = conn.id
    db.close()

    # Run sync again
    client.post(
        f"/api/bank-connections/{conn_id}/sync",
        headers={"Authorization": f"Bearer {user_alice['token']}"}
    )

    # Verify category remains intact
    db = TestingSessionLocal()
    re_tx = db.query(Transaction).filter_by(id=tx_id).first()
    assert re_tx.category == "Custom Category"
    assert re_tx.is_reviewed is True
    db.close()


# ==============================================================================
# 5. Safe Disconnect & Ledger Preservation
# ==============================================================================

def test_disconnect_bank_connection(user_alice):
    """Verify disconnecting bank deletes connection and accounts, but preserves ledger transactions."""
    db = TestingSessionLocal()
    u_id = user_alice["id"]
    conn = db.query(BankConnection).filter_by(user_id=u_id).first()
    conn_id = conn.id
    tx_count_before = db.query(Transaction).filter_by(user_id=u_id).count()
    assert tx_count_before > 0
    db.close()

    # Disconnect via API
    del_resp = client.delete(
        f"/api/bank-connections/{conn_id}",
        headers={"Authorization": f"Bearer {user_alice['token']}"}
    )
    assert del_resp.status_code == 204

    # Verify connection & accounts are deleted
    db = TestingSessionLocal()
    assert db.query(BankConnection).filter_by(id=conn_id).first() is None
    assert db.query(BankAccount).filter_by(connection_id=conn_id).count() == 0

    # Verify transactions are preserved in ledger with bank_account_id cleared
    tx_count_after = db.query(Transaction).filter_by(user_id=u_id).count()
    assert tx_count_after == tx_count_before
    for t in db.query(Transaction).filter_by(user_id=u_id).all():
        assert t.bank_account_id is None
    db.close()


# ==============================================================================
# 6. Authentication & Cross-User Data Isolation
# ==============================================================================

def test_unauthenticated_requests_rejected():
    """Verify 401 Unauthorized for unauthenticated calls."""
    assert client.get("/api/bank-connections").status_code == 401
    assert client.post("/api/bank-connections/connect", json={}).status_code == 401
    assert client.get("/api/bank-connections/providers").status_code == 401
    assert client.get("/api/bank-connections/123/accounts").status_code == 401
    assert client.post("/api/bank-connections/123/sync").status_code == 401
    assert client.delete("/api/bank-connections/123").status_code == 401


def test_cross_user_isolation(user_alice, user_bob):
    """Verify User Bob cannot access, sync, or delete User Alice's bank connection."""
    # Alice creates a connection
    alice_conn = client.post(
        "/api/bank-connections/connect",
        json={"provider": "mock", "institution_id": "ins_mock_hdfc"},
        headers={"Authorization": f"Bearer {user_alice['token']}"}
    ).json()
    conn_id = alice_conn["id"]

    # Bob lists connections: Alice's connection must NOT be visible
    bob_list = client.get(
        "/api/bank-connections",
        headers={"Authorization": f"Bearer {user_bob['token']}"}
    ).json()
    bob_conn_ids = [c["id"] for c in bob_list]
    assert conn_id not in bob_conn_ids

    # Bob tries to access Alice's accounts: 404
    assert client.get(
        f"/api/bank-connections/{conn_id}/accounts",
        headers={"Authorization": f"Bearer {user_bob['token']}"}
    ).status_code == 404

    # Bob tries to trigger sync on Alice's connection: 404
    assert client.post(
        f"/api/bank-connections/{conn_id}/sync",
        headers={"Authorization": f"Bearer {user_bob['token']}"}
    ).status_code == 404

    # Bob tries to delete Alice's connection: 404
    assert client.delete(
        f"/api/bank-connections/{conn_id}",
        headers={"Authorization": f"Bearer {user_bob['token']}"}
    ).status_code == 404
