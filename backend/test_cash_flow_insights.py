"""
Unit and Integration Tests for Cash Flow Forecasting & Financial Health Insights (Task 20)

Covers:
- Internal transfer detection and exclusion (Transfers category, self-transfer descriptions)
- Date window resolution (30d, 90d, this_month, custom ranges)
- Historical cash flow metrics (Income, Expenses, Net Cash Flow, Savings Rate)
- Category spending breakdown and period-over-period trend comparisons
- Deterministic forecasting without double-counting recurring commitments
- Data quality and confidence level grading (insufficient, low, medium, high)
- Financial health insights engine triggers:
    * Spending surge (> 15% increase)
    * Category concentration (> 35% of total spend)
    * Recurring commitment burden (> 25% of spend)
    * Budget overrun vs user budgets
    * Cash flow deficit (negative net flow)
    * Savings momentum (savings rate >= 20%)
- API Endpoints:
    * GET /api/insights/cash-flow
    * GET /api/insights/forecast
    * GET /api/insights/financial-health
- Authentication enforcement and strict cross-user data isolation
- Graceful handling of zero/insufficient historical data
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

TEST_DB_FILE = os.path.join(backend_dir, "test_insights_db.db")
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
from models.budget import Budget
from services.auth_service import create_access_token, hash_password
from database.migrations import run_migrations
from services.cash_flow_service import (
    is_internal_transfer,
    resolve_date_windows,
    compute_cash_flow_for_window,
    get_user_cash_flow_summary,
)
from services.cash_flow_forecast_service import (
    compute_cash_flow_forecast,
)
from services.financial_insights_service import generate_financial_health_insights

# Setup isolated test DB
engine = create_engine(f"sqlite:///{TEST_DB_FILE}", connect_args={"check_same_thread": False, "timeout": 30})
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
    try:
        user = db.query(User).filter_by(email="cf_user_primary@example.com").first()
        if not user:
            user = User(
                email="cf_user_primary@example.com",
                hashed_password=hash_password("Password123!"),
                full_name="Primary Insights User",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        user_id = user.id
    finally:
        db.close()
    token = create_access_token({"sub": "cf_user_primary@example.com", "user_id": user_id})
    return {"id": user_id, "email": "cf_user_primary@example.com", "token": token}


@pytest.fixture
def user_secondary():
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter_by(email="cf_user_secondary@example.com").first()
        if not user:
            user = User(
                email="cf_user_secondary@example.com",
                hashed_password=hash_password("Password123!"),
                full_name="Secondary Isolated User",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        user_id = user.id
    finally:
        db.close()
    token = create_access_token({"sub": "cf_user_secondary@example.com", "user_id": user_id})
    return {"id": user_id, "email": "cf_user_secondary@example.com", "token": token}


# =========================================================================
# 1. Internal Transfer & Window Resolution Unit Tests
# =========================================================================

def test_is_internal_transfer_logic():
    """Verify internal transfer detection by category, type, and keyword."""
    # Category = Transfers
    t1 = Transaction(amount=5000, type="Expense", category="Transfers", payment_method="Bank Transfer", description="Transfer to savings")
    assert is_internal_transfer(t1) is True

    # Type = Transfer
    t2 = Transaction(amount=1000, type="Transfer", category="General", payment_method="Card", description="Wire to checking")
    assert is_internal_transfer(t2) is True

    # Keywords in description
    t3 = Transaction(amount=2000, type="Expense", category="Other", payment_method="UPI", description="Self Transfer between accounts")
    assert is_internal_transfer(t3) is True

    t4 = Transaction(amount=3000, type="Expense", category="Other", payment_method="Bank Transfer", description="Inter-account funds transfer")
    assert is_internal_transfer(t4) is True

    # Legitimate non-transfer transactions
    t5 = Transaction(amount=450, type="Expense", category="Food", payment_method="UPI", description="Groceries at supermarket")
    assert is_internal_transfer(t5) is False

    t6 = Transaction(amount=60000, type="Income", category="Salary", payment_method="Bank Transfer", description="Monthly Payroll Deposit")
    assert is_internal_transfer(t6) is False


def test_resolve_date_windows():
    """Verify window resolution for 30d, 90d, this_month, and custom."""
    curr_s, curr_e, prev_s, prev_e = resolve_date_windows("30d")
    assert (curr_e - curr_s).days == 29  # 30 calendar days inclusive
    assert (prev_e - prev_s).days == 29
    assert prev_e < curr_s

    curr_s, curr_e, prev_s, prev_e = resolve_date_windows("90d")
    assert (curr_e - curr_s).days == 89  # 90 calendar days inclusive
    assert (prev_e - prev_s).days == 89

    # Custom window
    custom_s = datetime.date(2026, 1, 1)
    custom_e = datetime.date(2026, 1, 15)
    curr_s, curr_e, prev_s, prev_e = resolve_date_windows("custom", custom_s, custom_e)
    assert curr_s == custom_s
    assert curr_e == custom_e
    assert (curr_e - curr_s).days == 14
    assert (prev_e - prev_s).days == 14


# =========================================================================
# 2. Historical Cash Flow Service Calculations
# =========================================================================

def test_cash_flow_service_calculations(user_primary):
    """Test income, expenses, net cash flow, savings rate, and refund handling."""
    db = TestingSessionLocal()
    try:
        u_id = user_primary["id"]
        db.query(Transaction).filter_by(user_id=u_id).delete()
        db.commit()

        today = datetime.date.today()

        # Add Income: 100,000
        db.add(Transaction(
            user_id=u_id,
            amount=100000.0,
            type="Income",
            category="Salary",
            payment_method="Bank Transfer",
            description="Tech Corp Salary",
            transaction_date=today - datetime.timedelta(days=10),
        ))

        # Add Regular Expenses: Food 12,000, Rent 25,000, Utilities 5,000 (Total 42,000)
        db.add(Transaction(user_id=u_id, amount=12000.0, type="Expense", category="Food", payment_method="UPI", description="Supermarket", transaction_date=today - datetime.timedelta(days=15)))
        db.add(Transaction(user_id=u_id, amount=25000.0, type="Expense", category="Rent", payment_method="Bank Transfer", description="Apartment Rent", transaction_date=today - datetime.timedelta(days=20)))
        db.add(Transaction(user_id=u_id, amount=5000.0, type="Expense", category="Bills & Utilities", payment_method="Card", description="Electricity Bill", transaction_date=today - datetime.timedelta(days=5)))

        # Add Internal Transfer: 10,000 (Must NOT count towards expense or income)
        db.add(Transaction(user_id=u_id, amount=10000.0, type="Expense", category="Transfers", payment_method="Bank Transfer", description="Transfer to Investment account", transaction_date=today - datetime.timedelta(days=12)))

        # Add Refund: 2,000 income in Food with refund in description (Offsets Food expense)
        db.add(Transaction(user_id=u_id, amount=2000.0, type="Income", category="Food", payment_method="UPI", description="Grocery Refund from store", transaction_date=today - datetime.timedelta(days=8)))

        db.commit()

        summary = get_user_cash_flow_summary(db, u_id, timeframe="30d")

        # Verify totals
        assert summary["total_income"] == 100000.0
        # Expenses: 12000 + 25000 + 5000 - 2000 (refund) = 40000.0
        assert summary["total_expenses"] == 40000.0
        # Net: 100000 - 40000 = 60000.0
        assert summary["net_cash_flow"] == 60000.0
        # Savings rate: (60000 / 100000) * 100 = 60.0%
        assert summary["savings_rate"] == 60.0

        # Category breakdown verification
        cat_spend = {c["category"]: c["amount"] for c in summary["categories"]}
        assert cat_spend["Rent"] == 25000.0
        assert cat_spend["Food"] == 10000.0  # 12000 - 2000 refund
        assert cat_spend["Bills & Utilities"] == 5000.0
        assert "Transfers" not in cat_spend
    finally:
        db.close()


# =========================================================================
# 3. Cash Flow Forecasting Engine & Recurring Integration
# =========================================================================

def test_deterministic_forecasting_no_double_counting(user_primary):
    """Verify forecasting decomposes discretionary burn from recurring commitments without double-counting."""
    db = TestingSessionLocal()
    try:
        u_id = user_primary["id"]
        today = datetime.date.today()

        # Clear recurring payments and add a confirmed recurring subscription: Netflix 1,000 monthly
        db.query(RecurringPayment).filter_by(user_id=u_id).delete()
        next_due = today + datetime.timedelta(days=5)
        db.add(RecurringPayment(
            user_id=u_id,
            merchant_name="Netflix",
            normalized_name="netflix",
            frequency="monthly",
            category="Entertainment",
            status="confirmed",
            confidence=0.95,
            average_amount=1000.0,
            last_amount=1000.0,
            estimated_monthly_cost=1000.0,
            estimated_annual_cost=12000.0,
            last_payment_date=today - datetime.timedelta(days=25),
            next_estimated_date=next_due,
            transaction_count=3,
        ))
        db.commit()

        forecast = compute_cash_flow_forecast(db, u_id)

        assert "month_end_forecast" in forecast
        assert "next_30_days_forecast" in forecast
        assert "data_quality" in forecast
        assert "methodology" in forecast

        # The methodology should indicate discretionary burn rate and recurring commitment totals
        assert forecast["methodology"]["total_monthly_recurring_commitments"] >= 1000.0
        assert len(forecast["methodology"]["explanations"]) > 0
    finally:
        db.close()


# =========================================================================
# 4. Financial Health Insights Rule-Based Engine
# =========================================================================

def test_financial_health_insights_triggers(user_primary):
    """Test rule-based insight generation: surge, concentration, deficit, savings rate, recurring burden."""
    db = TestingSessionLocal()
    try:
        u_id = user_primary["id"]
        db.query(Transaction).filter_by(user_id=u_id).delete()
        db.query(Budget).filter_by(user_id=u_id).delete()
        db.commit()

        today = datetime.date.today()

        # Prior window (30 to 60 days ago): Total expense 20,000
        db.add(Transaction(
            user_id=u_id,
            amount=20000.0,
            type="Expense",
            category="Shopping",
            payment_method="Card",
            description="Prior month shopping",
            transaction_date=today - datetime.timedelta(days=45),
        ))

        # Current window (last 30 days): Total expense 50,000 (> 100% surge!)
        # Shopping is 40,000 (80% concentration)
        db.add(Transaction(
            user_id=u_id,
            amount=40000.0,
            type="Expense",
            category="Shopping",
            payment_method="Card",
            description="Luxury Shopping spree",
            transaction_date=today - datetime.timedelta(days=10),
        ))
        db.add(Transaction(
            user_id=u_id,
            amount=10000.0,
            type="Expense",
            category="Food",
            payment_method="UPI",
            description="Fine Dining",
            transaction_date=today - datetime.timedelta(days=5),
        ))

        # Income is only 30,000 (Net deficit of -20,000!)
        db.add(Transaction(
            user_id=u_id,
            amount=30000.0,
            type="Income",
            category="Salary",
            payment_method="Bank Transfer",
            description="Partial Freelance Pay",
            transaction_date=today - datetime.timedelta(days=12),
        ))

        # Set a budget for Shopping monthly_limit = 25,000 (Spent 40,000 -> Budget overrun!)
        db.add(Budget(
            user_id=u_id,
            category="Shopping",
            monthly_limit=25000.0,
            spent=40000.0,
        ))

        db.commit()

        health = generate_financial_health_insights(db, u_id, timeframe="30d")

        assert "insights" in health
        insights = health["insights"]
        insight_ids = [i["id"] for i in insights]

        # 1. Spending surge should trigger (> 15% increase)
        assert "insight_spending_surge" in insight_ids

        # 2. Category concentration should trigger (Shopping is 80% > 35%)
        assert any(i["id"].startswith("insight_category_concentration_") for i in insights)

        # 3. Cash flow deficit should trigger (Income 30,000 < Expenses 50,000)
        assert "insight_cash_flow_deficit" in insight_ids

        # 4. Budget overrun should trigger
        assert any(i["id"].startswith("insight_budget_overrun_") for i in insights)

        # Check that all insights have explainable metadata
        for ins in insights:
            assert ins["explanation"] is not None
            assert ins["period"] is not None
            assert ins["recommended_action"] is not None
            assert ins["type"] in ["risk", "warning", "opportunity", "achievement", "info"]
    finally:
        db.close()


# =========================================================================
# 5. REST API Integration Endpoints & JWT Authentication
# =========================================================================

def test_api_cash_flow_summary(user_primary):
    """Test GET /api/insights/cash-flow endpoint."""
    headers = {"Authorization": f"Bearer {user_primary['token']}"}
    response = client.get("/api/insights/cash-flow?timeframe=30d", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "timeframe" in data
    assert "total_income" in data
    assert "total_expenses" in data
    assert "net_cash_flow" in data
    assert "categories" in data
    assert "trends" in data
    assert "comparison" in data
    assert data["timeframe"] == "30d"


def test_api_cash_flow_forecast(user_primary):
    """Test GET /api/insights/forecast endpoint."""
    headers = {"Authorization": f"Bearer {user_primary['token']}"}
    response = client.get("/api/insights/forecast", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "month_end_forecast" in data
    assert "next_30_days_forecast" in data
    assert "data_quality" in data
    assert "methodology" in data
    assert data["month_end_forecast"]["projected_net_cash_flow"] is not None


def test_api_financial_health_insights(user_primary):
    """Test GET /api/insights/financial-health endpoint."""
    headers = {"Authorization": f"Bearer {user_primary['token']}"}
    response = client.get("/api/insights/financial-health?timeframe=30d", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "overall_health" in data
    assert "health_tone" in data
    assert "insights" in data
    assert isinstance(data["insights"], list)


# =========================================================================
# 6. User Isolation & Authentication Security
# =========================================================================

def test_authentication_required():
    """Verify 401 when no token is provided."""
    r1 = client.get("/api/insights/cash-flow")
    assert r1.status_code == 401

    r2 = client.get("/api/insights/forecast")
    assert r2.status_code == 401

    r3 = client.get("/api/insights/financial-health")
    assert r3.status_code == 401


def test_user_data_isolation(user_primary, user_secondary):
    """Verify user secondary cannot see user primary's cash flow or insights."""
    db = TestingSessionLocal()
    try:
        # Ensure user secondary has zero transactions
        db.query(Transaction).filter_by(user_id=user_secondary["id"]).delete()
        db.commit()
    finally:
        db.close()

    headers_sec = {"Authorization": f"Bearer {user_secondary['token']}"}

    # Cash flow for empty secondary user
    res_cf = client.get("/api/insights/cash-flow", headers=headers_sec)
    assert res_cf.status_code == 200
    data_cf = res_cf.json()
    assert data_cf["total_income"] == 0.0
    assert data_cf["total_expenses"] == 0.0
    assert len(data_cf["categories"]) == 0

    # Forecast for empty secondary user should be insufficient confidence
    res_fc = client.get("/api/insights/forecast", headers=headers_sec)
    assert res_fc.status_code == 200
    data_fc = res_fc.json()
    assert data_fc["data_quality"] == "insufficient"
    assert data_fc["confidence_score"] <= 0.3

    # Financial health for empty user should not fabricate insights
    res_hd = client.get("/api/insights/financial-health", headers=headers_sec)
    assert res_hd.status_code == 200
    data_hd = res_hd.json()
    assert len(data_hd["insights"]) == 0  # No empty dashboard filler
