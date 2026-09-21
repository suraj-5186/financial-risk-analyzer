"""
Unit and Integration Tests for Bank Statement Auto-Categorization (Task 17)
Tests:
- Known merchant/description categorization
- Debit vs Credit directional classification
- Ambiguous and unknown transactions ("Needs Review")
- User-edited category preservation
- Bank statement CSV parsing with separate Debit/Credit columns
- Duplicate detection & prevention
- API endpoints: /parse-csv, /confirm-import, /auto-categorize
- Authentication & user isolation
- Invalid category handling
- Regression coverage for existing transaction APIs
"""

import os
import sys
import io
import datetime
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

TEST_DB_FILE = os.path.join(backend_dir, "test_auto_cat.db")
if os.path.exists(TEST_DB_FILE):
    os.remove(TEST_DB_FILE)

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE}"

from main import app
from models.base import Base
from database.session import get_db
from models.user import User
from models.transaction import Transaction
from services.auth_service import create_access_token, hash_password
from database.migrations import run_migrations
from services.categorization_service import (
    categorize_transaction,
    categorize_statement_row,
    normalize_category_name,
    AutoCategorizationEngine,
    ALL_VALID_CATEGORIES,
)
from services.report_service import parse_transactions_csv

# Setup test DB
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
def user_a():
    db = TestingSessionLocal()
    user = db.query(User).filter_by(email="cat_user_a@example.com").first()
    if not user:
        user = User(
            email="cat_user_a@example.com",
            hashed_password=hash_password("SecretPassword123!"),
            full_name="User Alpha",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    user_id = user.id
    db.close()
    token = create_access_token({"sub": "cat_user_a@example.com", "user_id": user_id})
    return {"id": user_id, "email": "cat_user_a@example.com", "token": token}


@pytest.fixture
def user_b():
    db = TestingSessionLocal()
    user = db.query(User).filter_by(email="cat_user_b@example.com").first()
    if not user:
        user = User(
            email="cat_user_b@example.com",
            hashed_password=hash_password("SecretPassword456!"),
            full_name="User Beta",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    user_id = user.id
    db.close()
    token = create_access_token({"sub": "cat_user_b@example.com", "user_id": user_id})
    return {"id": user_id, "email": "cat_user_b@example.com", "token": token}


# ==============================================================================
# 1. Known Merchant & Rule Categorization Tests
# ==============================================================================

def test_categorization_engine_known_merchants():
    """Verify known merchants across diverse categories achieve high confidence."""
    test_cases = [
        ("Swiggy Order #89234 Bangalore", "Expense", "Food", 0.85),
        ("Zomato Ltd Payment UPI", "Expense", "Food", 0.85),
        ("McDonalds Drive Thru Indiranagar", "Expense", "Food", 0.85),
        ("Starbucks Coffee Koramangala", "Expense", "Food", 0.85),
        ("Uber India Systems Pvt Ltd Ride", "Expense", "Transport", 0.85),
        ("Ola Cabs Trip #77123", "Expense", "Transport", 0.85),
        ("Shell Petrol Bunk Fuel refill", "Expense", "Transport", 0.85),
        ("Amazon Pay India Retail Purchase", "Expense", "Shopping", 0.85),
        ("Flipkart Internet Pvt Ltd", "Expense", "Shopping", 0.85),
        ("Zara Retail Store DLF Mall", "Expense", "Shopping", 0.85),
        ("Bescom Electricity Bill Payment", "Expense", "Bills & Utilities", 0.85),
        ("Airtel Postpaid Mobile Recharge", "Expense", "Bills & Utilities", 0.85),
        ("Apollo Pharmacy Medicines Bangalore", "Expense", "Healthcare", 0.85),
        ("Practo Consultation Fee Dr Sharma", "Expense", "Healthcare", 0.85),
        ("Netflix India Monthly Subscription", "Expense", "Entertainment", 0.85),
        ("Spotify Premium Family Plan", "Expense", "Entertainment", 0.85),
        ("House Rent Payment for Sep 2026", "Expense", "Rent", 0.85),
        ("Coursera Specialization Course Fee", "Expense", "Education", 0.85),
        ("Udemy Online Web Development", "Expense", "Education", 0.85),
        ("Salary Credit from Infosys BPM Ltd", "Income", "Salary", 0.85),
        ("Payroll Direct Deposit Tata Consultancy", "Income", "Salary", 0.85),
        ("Upwork Escrow Milestone Payment", "Income", "Freelance", 0.85),
        ("Zerodha Broking Dividend Payout", "Income", "Investment", 0.85),
    ]

    for desc, tx_type, expected_cat, min_confidence in test_cases:
        res = categorize_transaction(desc, tx_type)
        assert res["suggested_category"] == expected_cat, f"Failed for '{desc}': got {res['suggested_category']}, expected {expected_cat}"
        assert res["confidence"] >= min_confidence, f"Confidence too low for '{desc}': {res['confidence']}"
        assert res["rule_matched"] is not None


# ==============================================================================
# 2. Debit vs Credit Directional Classification Tests
# ==============================================================================

def test_debit_vs_credit_directional_classification():
    """Verify that transaction direction (Debit vs Credit) properly partitions categories."""
    # An ambiguous corporate party should be Salary or Client payout when Income, but Expense when Debit
    res_credit = categorize_transaction("Infosys Technologies Payout", "Income")
    assert res_credit["suggested_category"] in ["Salary", "Freelance", "Business", "Investment"]

    # When marked Expense, it should not be categorized as Salary
    res_debit = categorize_transaction("Payment to Infosys Cafeteria", "Expense")
    assert res_debit["suggested_category"] in ["Food", "Other", "Bills & Utilities"]

    # Bank statement row parser test with separate Debit and Credit columns
    row_credit = {
        "Transaction Date": "2026-09-15",
        "Narration": "SALARY CREDIT TECHCORP",
        "Withdrawal": "",
        "Deposit": "125000.00",
    }
    parsed_credit = categorize_statement_row(row_credit)
    assert parsed_credit["type"] == "Income"
    assert parsed_credit["amount"] == 125000.00
    assert parsed_credit["suggested_category"] == "Salary"

    row_debit = {
        "Transaction Date": "2026-09-16",
        "Narration": "UBER RIDE MUMBAI",
        "Withdrawal": "450.00",
        "Deposit": "",
    }
    parsed_debit = categorize_statement_row(row_debit)
    assert parsed_debit["type"] == "Expense"
    assert parsed_debit["amount"] == 450.00
    assert parsed_debit["suggested_category"] == "Transport"


# ==============================================================================
# 3. Ambiguous and Unknown Transactions ("Needs Review")
# ==============================================================================

def test_ambiguous_and_unknown_transactions():
    """Ambiguous or unidentifiable transactions must be flagged as 'Needs Review' with low confidence."""
    vague_descriptions = [
        "REF98127391823/XX90",
        "POS 998127732 AUTH 129881",
        "TXN 109283019283019283",
        "RANDOM MISC STRING WITHOUT HINTS",
        "MISC 991200",
    ]

    for desc in vague_descriptions:
        res = categorize_transaction(desc, "Expense")
        assert res["suggested_category"] == "Needs Review", f"Expected Needs Review for '{desc}', got '{res['suggested_category']}'"
        assert res["confidence"] < 0.70, f"Confidence should be < 0.70 for ambiguous '{desc}', got {res['confidence']}"
        assert "Ambiguous" in res["explanation"] or "Needs Review" in res["explanation"]


# ==============================================================================
# 4. User-Edited Category Preservation
# ==============================================================================

def test_user_edited_category_preservation():
    """Never overwrite a user-specified category, even if rules disagree."""
    # Description contains "Netflix" which normally maps to "Entertainment"
    # But user designated it as "Education" (e.g. documentary subscription)
    res = categorize_transaction(
        description="Netflix Subscription",
        transaction_type="Expense",
        existing_category="Education",
    )
    assert res["suggested_category"] == "Education"
    assert res["confidence"] == 1.0
    assert res["is_reviewed"] is True
    assert "Preserved" in res["explanation"]

    # Also test normalize_category_name alias handling
    assert normalize_category_name("Travel") == "Transport"
    assert normalize_category_name("Bills") == "Bills & Utilities"
    assert normalize_category_name("Utilities") == "Bills & Utilities"


# ==============================================================================
# 5. Bank Statement CSV Parser Integration
# ==============================================================================

def test_parse_transactions_csv_with_various_formats():
    """Verify parse_transactions_csv correctly handles standard and bank statement formats."""
    # Format 1: Standard CSV with Date, Description, Amount, Type
    csv_standard = (
        "Date,Description,Amount,Type\n"
        "2026-09-01,Swiggy Bangalore,450.00,Expense\n"
        "2026-09-02,Monthly Salary Credit,85000.00,Income\n"
        "2026-09-03,Unknown Ref 991238,1200.00,Expense\n"
    ).encode("utf-8")

    parsed_std = parse_transactions_csv(csv_standard)
    assert len(parsed_std) == 3
    assert parsed_std[0]["suggested_category"] == "Food"
    assert parsed_std[1]["suggested_category"] == "Salary"
    assert parsed_std[2]["suggested_category"] == "Needs Review"

    # Format 2: Bank Statement CSV with separate Debit/Credit columns
    csv_bank = (
        "Transaction Date,Narration,Withdrawal,Deposit,Balance\n"
        "05-09-2026,Uber India Trip,320.00,,54000.00\n"
        "06-09-2026,Upwork Escrow Freelance,,15000.00,69000.00\n"
    ).encode("utf-8")

    parsed_bank = parse_transactions_csv(csv_bank)
    assert len(parsed_bank) == 2
    assert parsed_bank[0]["type"] == "Expense"
    assert parsed_bank[0]["amount"] == 320.00
    assert parsed_bank[0]["suggested_category"] == "Transport"

    assert parsed_bank[1]["type"] == "Income"
    assert parsed_bank[1]["amount"] == 15000.00
    assert parsed_bank[1]["suggested_category"] == "Freelance"


# ==============================================================================
# 6. Duplicate Detection & Prevention in Database
# ==============================================================================

def test_duplicate_detection_via_parse_csv_endpoint(user_a):
    """Test duplicate detection in POST /api/transactions/parse-csv and deduplication."""
    token = user_a["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # First, insert a confirmed transaction in DB
    db = TestingSessionLocal()
    existing_tx = Transaction(
        user_id=user_a["id"],
        transaction_date=datetime.date(2026, 9, 10),
        amount=Decimal("1999.00"),
        type="Expense",
        category="Shopping",
        payment_method="Card",
        description="Amazon Pay Retail Order 9912",
        category_confidence=0.95,
        auto_category="Shopping",
        is_reviewed=True,
    )
    db.add(existing_tx)
    db.commit()
    db.close()

    # Now upload a CSV containing:
    # 1. Exact duplicate of the existing transaction
    # 2. A brand new transaction
    # 3. An internal duplicate within the same file batch
    csv_content = (
        "Date,Description,Amount,Type\n"
        "2026-09-10,Amazon Pay Retail Order 9912,1999.00,Expense\n"
        "2026-09-11,Swiggy Lunch,350.00,Expense\n"
        "2026-09-11,Swiggy Lunch,350.00,Expense\n"
    ).encode("utf-8")

    files = {"file": ("statement.csv", io.BytesIO(csv_content), "text/csv")}
    resp = client.post("/api/transactions/parse-csv", headers=headers, files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["total_parsed"] == 3
    assert data["duplicates_count"] == 2  # 1 from DB, 1 intra-file duplicate

    items = data["items"]
    # Item 0 matches existing DB record
    assert items[0]["is_duplicate"] is True
    assert "exists" in items[0]["duplicate_reason"].lower() or "identical" in items[0]["duplicate_reason"].lower()

    # Item 1 is new
    assert items[1]["is_duplicate"] is False
    assert items[1]["suggested_category"] == "Food"

    # Item 2 is intra-file duplicate of Item 1
    assert items[2]["is_duplicate"] is True
    assert "statement" in items[2]["duplicate_reason"].lower() or "duplicate" in items[2]["duplicate_reason"].lower()


# ==============================================================================
# 7. Confirm Import API Flow
# ==============================================================================

def test_confirm_import_api_flow(user_a):
    """Test importing selected items via POST /api/transactions/confirm-import."""
    token = user_a["token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "skip_duplicates": True,
        "items": [
            {
                "temp_id": "temp_01",
                "transaction_date": "2026-09-14",
                "type": "Expense",
                "amount": 420.00,
                "category": "Food",
                "auto_category": "Food",
                "category_confidence": 0.95,
                "payment_method": "UPI",
                "description": "Zomato Meal",
                "is_reviewed": True,
                "is_duplicate": False,
            },
            {
                "temp_id": "temp_02",
                "transaction_date": "2026-09-14",
                "type": "Income",
                "amount": 50000.00,
                "category": "Salary",
                "auto_category": "Salary",
                "category_confidence": 0.95,
                "payment_method": "Bank Transfer",
                "description": "Tech Salary Sep",
                "is_reviewed": True,
                "is_duplicate": False,
            },
        ],
    }

    resp = client.post("/api/transactions/confirm-import", headers=headers, json=payload)
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["imported_count"] == 2
    assert result["skipped_duplicates_count"] == 0

    # Verify rows exist in DB with appropriate metadata
    db = TestingSessionLocal()
    saved = db.query(Transaction).filter_by(user_id=user_a["id"], description="Zomato Meal").first()
    assert saved is not None
    assert saved.category == "Food"
    assert saved.auto_category == "Food"
    assert saved.category_confidence == 0.95
    assert saved.is_reviewed is True
    db.close()


# ==============================================================================
# 8. Single Auto-Categorize API Endpoint Test
# ==============================================================================

def test_auto_categorize_single_api(user_a):
    """Test the POST /api/transactions/auto-categorize utility endpoint."""
    token = user_a["token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "description": "Uber Ride to Airport Terminal 2",
        "type": "Expense",
    }
    resp = client.post("/api/transactions/auto-categorize", headers=headers, json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["suggested_category"] == "Transport"
    assert data["confidence"] >= 0.85
    assert data["needs_review"] is False


# ==============================================================================
# 9. Authentication & User Isolation
# ==============================================================================

def test_user_isolation_and_auth(user_a, user_b):
    """User B cannot access or modify User A's transactions."""
    # User A creates a transaction
    db = TestingSessionLocal()
    tx_a = Transaction(
        user_id=user_a["id"],
        transaction_date=datetime.date(2026, 9, 12),
        amount=Decimal("1500.00"),
        type="Expense",
        category="Healthcare",
        payment_method="UPI",
        description="User A Private Apollo Hospital",
        category_confidence=0.95,
    )
    db.add(tx_a)
    db.commit()
    db.refresh(tx_a)
    tx_a_id = tx_a.id
    db.close()

    # User B lists transactions -> should NOT contain tx_a
    resp_b_list = client.get(
        "/api/transactions/",
        headers={"Authorization": f"Bearer {user_b['token']}"},
    )
    assert resp_b_list.status_code == 200
    b_transactions = resp_b_list.json()
    b_ids = [t["id"] for t in b_transactions]
    assert tx_a_id not in b_ids

    # User B tries to delete tx_a -> should return 404
    resp_b_del = client.delete(
        f"/api/transactions/{tx_a_id}",
        headers={"Authorization": f"Bearer {user_b['token']}"},
    )
    assert resp_b_del.status_code == 404

    # Unauthenticated request to /parse-csv is rejected
    csv_bytes = b"Date,Description,Amount,Type\n2026-09-01,Test,10,Expense\n"
    resp_unauth = client.post(
        "/api/transactions/parse-csv",
        files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert resp_unauth.status_code == 401


# ==============================================================================
# 10. Invalid Category Handling
# ==============================================================================

def test_invalid_category_handling(user_a):
    """Invalid or malicious category strings are cleanly rejected or normalized."""
    token = user_a["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to confirm import with an unsupported category
    payload = {
        "skip_duplicates": True,
        "items": [
            {
                "temp_id": "temp_bad_cat",
                "transaction_date": "2026-09-15",
                "type": "Expense",
                "amount": 100.00,
                "category": "BogusCategory123",
                "payment_method": "UPI",
                "description": "Bad Category Test",
            }
        ],
    }
    resp = client.post("/api/transactions/confirm-import", headers=headers, json=payload)
    assert resp.status_code in [400, 422]


# ==============================================================================
# 11. Regression Coverage for Existing CSV Import
# ==============================================================================

def test_legacy_import_csv_backward_compatibility(user_a):
    """Ensure existing POST /api/transactions/import-csv continues to work seamlessly."""
    token = user_a["token"]
    headers = {"Authorization": f"Bearer {token}"}

    csv_data = (
        "Date,Description,Amount,Type,Category\n"
        "2026-09-08,Airtel Broadband,999.00,Expense,Bills & Utilities\n"
    ).encode("utf-8")

    files = {"file": ("legacy.csv", io.BytesIO(csv_data), "text/csv")}
    resp = client.post("/api/transactions/import-csv", headers=headers, files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "imported" in data["message"].lower()

    # Verify it exists in DB
    db = TestingSessionLocal()
    found = db.query(Transaction).filter_by(
        user_id=user_a["id"], description="Airtel Broadband"
    ).first()
    assert found is not None
    assert found.category == "Bills & Utilities"
    db.close()
