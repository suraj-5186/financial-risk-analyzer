"""
Unit and Integration Tests for Recurring Subscription & Payment Detector (Task 18)

Covers:
- Merchant normalization and transient token removal
- Frequency detection: Monthly, Weekly, Biweekly, Quarterly, Annual
- Amount variance handling: Exact subscription vs variable utility bills
- Rejection of irregular shopping / false positives
- Rejection of insufficient history (< 2 transactions)
- Exclusion of Income and Transfers
- Cost normalization (weekly, biweekly, monthly, quarterly, annual)
- Next payment date projection
- Confidence scoring logic
- Database persistence and idempotent rescanning
- Preservation of user confirmation and dismissal decisions
- API Endpoints: GET, POST /scan, GET /summary, PATCH /{id}, DELETE /{id}
- Authentication and cross-user data isolation
"""

import os
import sys
import datetime
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

TEST_DB_FILE = os.path.join(backend_dir, "test_recurring_db.db")
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
from models.recurring_payment import RecurringPayment
from services.auth_service import create_access_token, hash_password
from database.migrations import run_migrations
from services.recurring_service import (
    normalize_merchant_name,
    calculate_normalized_costs,
    calculate_next_payment_date,
    RecurringPaymentDetector,
    scan_user_recurring_payments,
    get_recurring_summary,
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
def user_primary():
    db = TestingSessionLocal()
    user = db.query(User).filter_by(email="rec_user_primary@example.com").first()
    if not user:
        user = User(
            email="rec_user_primary@example.com",
            hashed_password=hash_password("Password123!"),
            full_name="Primary Subscriber",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    user_id = user.id
    db.close()
    token = create_access_token({"sub": "rec_user_primary@example.com", "user_id": user_id})
    return {"id": user_id, "email": "rec_user_primary@example.com", "token": token}


@pytest.fixture
def user_secondary():
    db = TestingSessionLocal()
    user = db.query(User).filter_by(email="rec_user_secondary@example.com").first()
    if not user:
        user = User(
            email="rec_user_secondary@example.com",
            hashed_password=hash_password("Password456!"),
            full_name="Secondary User",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    user_id = user.id
    db.close()
    token = create_access_token({"sub": "rec_user_secondary@example.com", "user_id": user_id})
    return {"id": user_id, "email": "rec_user_secondary@example.com", "token": token}


# ==============================================================================
# 1. Unit Tests: Normalization & Mathematical Cost Calculations
# ==============================================================================

def test_merchant_name_normalization():
    """Verify description cleansing, transient token removal, and canonical matching."""
    # Known canonical subscriptions
    assert normalize_merchant_name("NETFLIX.COM PAYMENT 98124") == "Netflix"
    assert normalize_merchant_name("UPI-SPOTIFY INDIA-AUTOPAY") == "Spotify"
    assert normalize_merchant_name("AMAZON PRIME VIDEO SUBSCRIPTION") == "Amazon Prime"
    assert normalize_merchant_name("YOUTUBE PREMIUM RECURRING") == "YouTube Premium"
    assert normalize_merchant_name("AWS CLOUD SERVICES BILL 2026-05") == "AWS Cloud"
    assert normalize_merchant_name("GITHUB SPONSOR / MONTHLY") == "GitHub"
    assert normalize_merchant_name("OPENAI CHATGPT PLUS") == "OpenAI / ChatGPT"
    assert normalize_merchant_name("AIRTEL POSTPAID BILL PAYMENT") == "Airtel"
    assert normalize_merchant_name("BESCOM ELECTRICITY BILL BANGALORE") == "BESCOM Electricity"
    assert normalize_merchant_name("HOUSE RENT APARTMENT 402") == "Rent"
    assert normalize_merchant_name("CULTFIT FITNESS PASS") == "Cult.fit"

    # Transient token stripping for unknown merchants
    clean_pos = normalize_merchant_name("POS DEBIT **4412 BLUE DART EXP 2026-04-12")
    assert "Pos" not in clean_pos and "4412" not in clean_pos and "Blue Dart" in clean_pos


def test_cost_normalization_formulas():
    """Verify standard financial cost formulas across all frequencies."""
    # Weekly: amount * 52 / 12, amount * 52
    m, a = calculate_normalized_costs(100.0, "weekly")
    assert m == round(100.0 * 52.0 / 12.0, 2)  # 433.33
    assert a == 5200.0

    # Biweekly: amount * 26 / 12, amount * 26
    m, a = calculate_normalized_costs(500.0, "biweekly")
    assert m == round(500.0 * 26.0 / 12.0, 2)  # 1083.33
    assert a == 13000.0

    # Monthly: amount, amount * 12
    m, a = calculate_normalized_costs(649.0, "monthly")
    assert m == 649.0
    assert a == round(649.0 * 12.0, 2)  # 7788.0

    # Quarterly: amount / 3, amount * 4
    m, a = calculate_normalized_costs(3000.0, "quarterly")
    assert m == 1000.0
    assert a == 12000.0

    # Annual: amount / 12, amount
    m, a = calculate_normalized_costs(12000.0, "annual")
    assert m == 1000.0
    assert a == 12000.0


def test_next_payment_date_calculation():
    """Verify accurate forward projection of next estimated dates."""
    base_date = datetime.date(2026, 3, 15)

    # Weekly: +7 days
    assert calculate_next_payment_date(base_date, "weekly") == datetime.date(2026, 3, 22)

    # Biweekly: +14 days
    assert calculate_next_payment_date(base_date, "biweekly") == datetime.date(2026, 3, 29)

    # Monthly: +1 month preserving day
    assert calculate_next_payment_date(base_date, "monthly") == datetime.date(2026, 4, 15)

    # Monthly end of month adjustment (Jan 31 -> Feb 28)
    jan_31 = datetime.date(2026, 1, 31)
    assert calculate_next_payment_date(jan_31, "monthly") == datetime.date(2026, 2, 28)

    # Quarterly: +3 months
    assert calculate_next_payment_date(base_date, "quarterly") == datetime.date(2026, 6, 15)

    # Annual: +1 year
    assert calculate_next_payment_date(base_date, "annual") == datetime.date(2027, 3, 15)


# ==============================================================================
# 2. Engine Detection Logic: Frequencies, Variations, False Positive Rejection
# ==============================================================================

def test_engine_detects_monthly_subscription():
    """Verify detection of monthly fixed-amount subscription with high confidence."""
    detector = RecurringPaymentDetector()
    txs = [
        Transaction(id="1", user_id="1", description="Netflix Subscription", amount=649.00, type="Expense", category="Entertainment", transaction_date=datetime.date(2026, 1, 15), payment_method="Card"),
        Transaction(id="2", user_id="1", description="Netflix Subscription", amount=649.00, type="Expense", category="Entertainment", transaction_date=datetime.date(2026, 2, 15), payment_method="Card"),
        Transaction(id="3", user_id="1", description="Netflix Subscription", amount=649.00, type="Expense", category="Entertainment", transaction_date=datetime.date(2026, 3, 15), payment_method="Card"),
    ]
    detected = detector.analyze_transactions(txs)
    assert len(detected) == 1
    item = detected[0]
    assert item["merchant_name"] == "Netflix"
    assert item["normalized_name"] == "netflix"
    assert item["frequency"] == "monthly"
    assert item["average_amount"] == 649.0
    assert item["last_amount"] == 649.0
    assert item["transaction_count"] == 3
    assert item["confidence"] >= 0.85
    assert item["next_estimated_date"] == datetime.date(2026, 4, 15)


def test_engine_detects_weekly_and_biweekly():
    """Verify weekly and biweekly interval cadences."""
    detector = RecurringPaymentDetector()
    
    # Weekly milk delivery
    weekly_txs = [
        Transaction(id="10", user_id="1", description="Country Delight Milk", amount=350.00, type="Expense", category="Food", transaction_date=datetime.date(2026, 3, 1), payment_method="UPI"),
        Transaction(id="11", user_id="1", description="Country Delight Milk", amount=350.00, type="Expense", category="Food", transaction_date=datetime.date(2026, 3, 8), payment_method="UPI"),
        Transaction(id="12", user_id="1", description="Country Delight Milk", amount=350.00, type="Expense", category="Food", transaction_date=datetime.date(2026, 3, 15), payment_method="UPI"),
    ]
    detected = detector.analyze_transactions(weekly_txs)
    assert len(detected) == 1
    assert detected[0]["frequency"] == "weekly"
    assert detected[0]["estimated_monthly_cost"] == round(350.0 * 52 / 12, 2)

    # Biweekly cleaning
    biweekly_txs = [
        Transaction(id="20", user_id="1", description="Urban Company Home Cleaning", amount=1200.00, type="Expense", category="Services", transaction_date=datetime.date(2026, 2, 1), payment_method="UPI"),
        Transaction(id="21", user_id="1", description="Urban Company Home Cleaning", amount=1200.00, type="Expense", category="Services", transaction_date=datetime.date(2026, 2, 15), payment_method="UPI"),
        Transaction(id="22", user_id="1", description="Urban Company Home Cleaning", amount=1200.00, type="Expense", category="Services", transaction_date=datetime.date(2026, 3, 1), payment_method="UPI"),
    ]
    detected_bi = detector.analyze_transactions(biweekly_txs)
    assert len(detected_bi) == 1
    assert detected_bi[0]["frequency"] == "biweekly"


def test_engine_detects_quarterly_and_annual():
    """Verify quarterly and annual recurring intervals."""
    detector = RecurringPaymentDetector()
    
    # Quarterly water maintenance
    quarterly_txs = [
        Transaction(id="30", user_id="1", description="Society Water Maintenance", amount=4500.00, type="Expense", category="Housing", transaction_date=datetime.date(2025, 6, 10), payment_method="UPI"),
        Transaction(id="31", user_id="1", description="Society Water Maintenance", amount=4500.00, type="Expense", category="Housing", transaction_date=datetime.date(2025, 9, 10), payment_method="UPI"),
        Transaction(id="32", user_id="1", description="Society Water Maintenance", amount=4500.00, type="Expense", category="Housing", transaction_date=datetime.date(2025, 12, 10), payment_method="UPI"),
    ]
    detected_q = detector.analyze_transactions(quarterly_txs)
    assert len(detected_q) == 1
    assert detected_q[0]["frequency"] == "quarterly"
    assert detected_q[0]["estimated_monthly_cost"] == 1500.0

    # Annual term insurance
    annual_txs = [
        Transaction(id="40", user_id="1", description="HDFC Life Insurance Premium", amount=24000.00, type="Expense", category="Insurance", transaction_date=datetime.date(2024, 5, 20), payment_method="NetBanking"),
        Transaction(id="41", user_id="1", description="HDFC Life Insurance Premium", amount=24000.00, type="Expense", category="Insurance", transaction_date=datetime.date(2025, 5, 20), payment_method="NetBanking"),
    ]
    detected_a = detector.analyze_transactions(annual_txs)
    assert len(detected_a) == 1
    assert detected_a[0]["frequency"] == "annual"
    assert detected_a[0]["estimated_monthly_cost"] == 2000.0


def test_engine_handles_variable_utility_bills():
    """Verify detection of recurring bills with modest amount variation (e.g. electricity)."""
    detector = RecurringPaymentDetector()
    txs = [
        Transaction(id="50", user_id="1", description="BESCOM Electricity Bill", amount=1250.00, type="Expense", category="Bills & Utilities", transaction_date=datetime.date(2026, 1, 5), payment_method="UPI"),
        Transaction(id="51", user_id="1", description="BESCOM Electricity Bill", amount=1380.00, type="Expense", category="Bills & Utilities", transaction_date=datetime.date(2026, 2, 5), payment_method="UPI"),
        Transaction(id="52", user_id="1", description="BESCOM Electricity Bill", amount=1190.00, type="Expense", category="Bills & Utilities", transaction_date=datetime.date(2026, 3, 5), payment_method="UPI"),
    ]
    detected = detector.analyze_transactions(txs)
    assert len(detected) == 1
    assert detected[0]["merchant_name"] == "BESCOM Electricity"
    assert detected[0]["normalized_name"] == "bescom electricity"
    assert detected[0]["frequency"] == "monthly"
    assert detected[0]["last_amount"] == 1190.0
    # Average amount should reflect mean (~1273.33)
    assert 1270.0 <= detected[0]["average_amount"] <= 1280.0


def test_engine_rejects_irregular_shopping_and_insufficient_history():
    """Ensure random shopping purchases and single transactions are NOT flagged as recurring."""
    detector = RecurringPaymentDetector()

    # 1. Irregular Amazon purchases (different dates, wild amount variance > 30%)
    irregular_shopping = [
        Transaction(id="60", user_id="1", description="Amazon Retail Purchase", amount=249.00, type="Expense", category="Shopping", transaction_date=datetime.date(2026, 1, 3), payment_method="Card"),
        Transaction(id="61", user_id="1", description="Amazon Retail Purchase", amount=4500.00, type="Expense", category="Shopping", transaction_date=datetime.date(2026, 1, 9), payment_method="Card"),
        Transaction(id="62", user_id="1", description="Amazon Retail Purchase", amount=89.00, type="Expense", category="Shopping", transaction_date=datetime.date(2026, 2, 2), payment_method="Card"),
    ]
    detected_shop = detector.analyze_transactions(irregular_shopping)
    assert len(detected_shop) == 0

    # 2. Single transaction has insufficient history (< 2)
    single_tx = [
        Transaction(id="70", user_id="1", description="Gym Membership", amount=2500.00, type="Expense", category="Healthcare", transaction_date=datetime.date(2026, 3, 1), payment_method="Card"),
    ]
    detected_single = detector.analyze_transactions(single_tx)
    assert len(detected_single) == 0


def test_engine_excludes_income_and_transfers():
    """Verify Income transactions and account transfers are strictly excluded."""
    detector = RecurringPaymentDetector()
    txs = [
        # Regular monthly salary (should NOT be detected as subscription expense)
        Transaction(id="80", user_id="1", description="Tech Corp Monthly Salary", amount=150000.00, type="Income", category="Income", transaction_date=datetime.date(2026, 1, 1), payment_method="Bank Transfer"),
        Transaction(id="81", user_id="1", description="Tech Corp Monthly Salary", amount=150000.00, type="Income", category="Income", transaction_date=datetime.date(2026, 2, 1), payment_method="Bank Transfer"),
        Transaction(id="82", user_id="1", description="Tech Corp Monthly Salary", amount=150000.00, type="Income", category="Income", transaction_date=datetime.date(2026, 3, 1), payment_method="Bank Transfer"),
        # Account transfer
        Transaction(id="83", user_id="1", description="Self Account Transfer Savings", amount=25000.00, type="Transfer", category="Transfer", transaction_date=datetime.date(2026, 1, 10), payment_method="Bank Transfer"),
        Transaction(id="84", user_id="1", description="Self Account Transfer Savings", amount=25000.00, type="Transfer", category="Transfer", transaction_date=datetime.date(2026, 2, 10), payment_method="Bank Transfer"),
    ]
    detected = detector.analyze_transactions(txs)
    assert len(detected) == 0


# ==============================================================================
# 3. API Integration & Idempotent Rescanning Tests
# ==============================================================================

def test_recurring_api_scan_and_list(user_primary):
    """Seed user transactions, run scan API, and verify detected records via GET."""
    db = TestingSessionLocal()
    u_id = user_primary["id"]

    # Clean old records for user_primary
    db.query(RecurringPayment).filter_by(user_id=u_id).delete()
    db.query(Transaction).filter_by(user_id=u_id).delete()
    db.commit()

    # Seed monthly Spotify and monthly Broadband
    tx1 = Transaction(user_id=u_id, description="Spotify Premium Individual", amount=119.00, type="Expense", category="Entertainment", transaction_date=datetime.date(2026, 1, 10), payment_method="Card")
    tx2 = Transaction(user_id=u_id, description="Spotify Premium Individual", amount=119.00, type="Expense", category="Entertainment", transaction_date=datetime.date(2026, 2, 10), payment_method="Card")
    tx3 = Transaction(user_id=u_id, description="Spotify Premium Individual", amount=119.00, type="Expense", category="Entertainment", transaction_date=datetime.date(2026, 3, 10), payment_method="Card")
    
    tx4 = Transaction(user_id=u_id, description="ACT Fibernet Broadband", amount=943.00, type="Expense", category="Bills & Utilities", transaction_date=datetime.date(2026, 1, 20), payment_method="UPI")
    tx5 = Transaction(user_id=u_id, description="ACT Fibernet Broadband", amount=943.00, type="Expense", category="Bills & Utilities", transaction_date=datetime.date(2026, 2, 20), payment_method="UPI")
    tx6 = Transaction(user_id=u_id, description="ACT Fibernet Broadband", amount=943.00, type="Expense", category="Bills & Utilities", transaction_date=datetime.date(2026, 3, 20), payment_method="UPI")

    db.add_all([tx1, tx2, tx3, tx4, tx5, tx6])
    db.commit()
    db.close()

    # 1. Trigger Scan API
    scan_resp = client.post(
        "/api/recurring-payments/scan",
        headers={"Authorization": f"Bearer {user_primary['token']}"}
    )
    assert scan_resp.status_code == 200
    scan_data = scan_resp.json()
    assert scan_data["total_active_count"] >= 2
    assert len(scan_data["items"]) >= 2
    assert "Scan completed" in scan_data["message"]

    # 2. List Recurring Payments
    list_resp = client.get(
        "/api/recurring-payments",
        headers={"Authorization": f"Bearer {user_primary['token']}"}
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) >= 2

    names = [it["normalized_name"] for it in items]
    assert "spotify" in names


def test_user_confirmation_and_dismissal_preservation(user_primary):
    """Verify PATCH endpoint confirms/dismisses, and rescanning preserves these user decisions."""
    # List items to get IDs
    list_resp = client.get(
        "/api/recurring-payments",
        headers={"Authorization": f"Bearer {user_primary['token']}"}
    )
    items = list_resp.json()
    assert len(items) >= 2

    spotify_item = next(it for it in items if "spotify" in it["normalized_name"].lower())
    other_item = next(it for it in items if it["id"] != spotify_item["id"])

    # 1. User confirms Spotify
    patch_resp1 = client.patch(
        f"/api/recurring-payments/{spotify_item['id']}",
        json={"status": "confirmed"},
        headers={"Authorization": f"Bearer {user_primary['token']}"}
    )
    assert patch_resp1.status_code == 200
    assert patch_resp1.json()["status"] == "confirmed"

    # 2. User dismisses the other item
    patch_resp2 = client.patch(
        f"/api/recurring-payments/{other_item['id']}",
        json={"status": "dismissed"},
        headers={"Authorization": f"Bearer {user_primary['token']}"}
    )
    assert patch_resp2.status_code == 200
    assert patch_resp2.json()["status"] == "dismissed"

    # 3. Rescan user transactions — IDEMPOTENCY CHECK
    rescan_resp = client.post(
        "/api/recurring-payments/scan",
        headers={"Authorization": f"Bearer {user_primary['token']}"}
    )
    assert rescan_resp.status_code == 200

    # 4. Verify decisions were NOT overwritten by rescan
    check_resp = client.get(
        "/api/recurring-payments",
        headers={"Authorization": f"Bearer {user_primary['token']}"}
    )
    updated_items = check_resp.json()
    updated_spotify = next(it for it in updated_items if it["id"] == spotify_item["id"])
    updated_other = next(it for it in updated_items if it["id"] == other_item["id"])

    assert updated_spotify["status"] == "confirmed"
    assert updated_other["status"] == "dismissed"


def test_recurring_summary_endpoint(user_primary):
    """Verify /summary metrics exclude dismissed subscriptions and compute correct totals."""
    summary_resp = client.get(
        "/api/recurring-payments/summary",
        headers={"Authorization": f"Bearer {user_primary['token']}"}
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()

    # The dismissed item must NOT count towards active_subscriptions_count or monthly commitment
    assert summary["dismissed_count"] >= 1
    assert summary["confirmed_count"] >= 1
    assert summary["total_monthly_commitment"] >= 119.0  # Spotify monthly
    assert summary["total_annual_commitment"] >= round(119.0 * 12, 2)
    assert isinstance(summary["upcoming_payments_next_30_days"], list)


def test_recurring_delete_endpoint(user_primary):
    """Verify DELETE /api/recurring-payments/{id} correctly removes records."""
    db = TestingSessionLocal()
    # Add a temporary record to delete
    temp_item = RecurringPayment(
        user_id=user_primary["id"],
        merchant_name="Temp Subscription",
        normalized_name="Temp Sub",
        category="Entertainment",
        frequency="monthly",
        average_amount=199.00,
        last_amount=199.00,
        estimated_monthly_cost=199.00,
        estimated_annual_cost=2388.00,
        confidence=0.8,
        status="detected",
        last_payment_date=datetime.date(2026, 3, 1),
        transaction_count=2,
    )
    db.add(temp_item)
    db.commit()
    db.refresh(temp_item)
    item_id = temp_item.id
    db.close()

    del_resp = client.delete(
        f"/api/recurring-payments/{item_id}",
        headers={"Authorization": f"Bearer {user_primary['token']}"}
    )
    assert del_resp.status_code == 204

    # Verify not found on subsequent delete
    del_again = client.delete(
        f"/api/recurring-payments/{item_id}",
        headers={"Authorization": f"Bearer {user_primary['token']}"}
    )
    assert del_again.status_code == 404


# ==============================================================================
# 4. Authentication & Cross-User Isolation Tests
# ==============================================================================

def test_unauthenticated_requests_rejected():
    """Verify 401 Unauthorized for unauthenticated calls."""
    assert client.get("/api/recurring-payments").status_code == 401
    assert client.post("/api/recurring-payments/scan").status_code == 401
    assert client.get("/api/recurring-payments/summary").status_code == 401
    assert client.patch("/api/recurring-payments/1", json={"status": "confirmed"}).status_code == 401
    assert client.delete("/api/recurring-payments/1").status_code == 401


def test_user_data_isolation(user_primary, user_secondary):
    """Verify User B cannot see, modify, or delete User A's recurring payments."""
    # User A creates a private subscription
    db = TestingSessionLocal()
    user_a_payment = RecurringPayment(
        user_id=user_primary["id"],
        merchant_name="User A Confidential Service",
        normalized_name="User A Confidential",
        frequency="monthly",
        average_amount=Decimal("5000.00"),
        last_amount=Decimal("5000.00"),
        estimated_monthly_cost=5000.00,
        estimated_annual_cost=60000.00,
        confidence=0.9,
        status="detected",
        last_payment_date=datetime.date(2026, 3, 1),
        transaction_count=3,
    )
    db.add(user_a_payment)
    db.commit()
    db.refresh(user_a_payment)
    p_id = user_a_payment.id
    db.close()

    # User B lists payments: should NOT contain User A's confidential service
    b_list = client.get(
        "/api/recurring-payments",
        headers={"Authorization": f"Bearer {user_secondary['token']}"}
    )
    assert b_list.status_code == 200
    b_names = [it["merchant_name"] for it in b_list.json()]
    assert "User A Confidential Service" not in b_names

    # User B attempts to PATCH User A's recurring payment -> 404 Not Found
    b_patch = client.patch(
        f"/api/recurring-payments/{p_id}",
        json={"status": "confirmed"},
        headers={"Authorization": f"Bearer {user_secondary['token']}"}
    )
    assert b_patch.status_code == 404

    # User B attempts to DELETE User A's recurring payment -> 404 Not Found
    b_delete = client.delete(
        f"/api/recurring-payments/{p_id}",
        headers={"Authorization": f"Bearer {user_secondary['token']}"}
    )
    assert b_delete.status_code == 404
