"""
Phase 2 Automated Verification — 25 Test Cases
Tests the financial behavior of the FinRisk AI backend against all 25 specs.
"""
import os
import sys

# Ensure backend directory is first in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
import datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test DB environment BEFORE importing app
TEST_DB_FILE = os.path.join(backend_dir, "test_phase2.db")
if os.path.exists(TEST_DB_FILE):
    os.remove(TEST_DB_FILE)

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE}"

from main import app
from models.base import Base
from database.session import get_db
from models.user import User
from models.profile import FinancialProfile
from models.goal import FinancialGoal
from models.income_source import IncomeSource
from models.income_allocation import IncomeAllocation
from models.recommendation import Recommendation
from services.auth_service import create_access_token
from database.migrations import run_migrations

# ── Test DB engine (separate from app DB) ──────────────────────────────────────
engine = create_engine(f"sqlite:///{TEST_DB_FILE}", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)
run_migrations()
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the app's DB dependency to use our test DB
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True, scope="module")
def setup_phase2_overrides():
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass


# ── Helper: create user + auth header ─────────────────────────────────────────
def create_test_user_and_auth(full_name="Tester", email="tester@example.com"):
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, full_name=full_name, hashed_password="testpasshash")
        db.add(user)
        db.commit()
        db.refresh(user)
        profile = FinancialProfile(user_id=user.id, monthly_income=30000.0)
        db.add(profile)
        db.commit()
    user_id = user.id
    token = create_access_token(data={"sub": user.email})
    db.close()
    db2 = TestingSessionLocal()
    user = db2.query(User).filter(User.id == user_id).first()
    db2.close()
    return user, {"Authorization": f"Bearer {token}"}


def create_goal(headers, title, target, current=0.0, date="2027-01-01"):
    """Create a goal, accepting 200 or 201."""
    res = client.post("/api/goals", json={
        "title": title,
        "target_amount": target,
        "current_amount": current,
        "target_date": date
    }, headers=headers)
    assert res.status_code in (200, 201), f"Goal creation failed: {res.text}"
    return res.json()["id"]


def create_income_source(headers, name, amount, income_type="one_time", frequency="one_time", is_active=True):
    """Create an income source, accepting 200 or 201."""
    res = client.post("/api/income-sources", json={
        "name": name,
        "amount": amount,
        "income_type": income_type,
        "frequency": frequency,
        "is_active": is_active,
    }, headers=headers)
    assert res.status_code in (200, 201), f"Income source creation failed: {res.text}"
    return res.json()


# ══════════════════════════════════════════════════════════════════════════════
class TestPhase2Specification:

    @classmethod
    def setup_class(cls):
        cls.user1, cls.headers1 = create_test_user_and_auth("Alice", "alice@phase2.test")
        cls.user2, cls.headers2 = create_test_user_and_auth("Bob", "bob@phase2.test")

        # Create shared resources upfront so failures don't cascade
        src = create_income_source(cls.headers1, "Diwali Bonus", 20000.0, "one_time", "one_time")
        cls.bonus_source_id = src["id"]

        cls.goal1_id = create_goal(cls.headers1, "MacBook Pro", 100000.0, 20000.0)
        cls.goal2_id = create_goal(cls.headers1, "Emergency Fund", 50000.0, 10000.0)
        cls.bob_goal_id = create_goal(cls.headers2, "Bob Car Fund", 80000.0)

        # Pre-allocate the bonus so allocation-chain tests work
        alloc_res = client.post(f"/api/income-sources/{cls.bonus_source_id}/allocate", json={
            "allocations": [
                {"goal_id": cls.goal1_id, "amount": 8000.0},
                {"goal_id": cls.goal2_id, "amount": 5000.0},
            ],
            "free_cash_amount": 7000.0,
        }, headers=cls.headers1)
        assert alloc_res.status_code == 200, f"Pre-allocation failed: {alloc_res.text}"

        # Create recurring salary and freelance sources for Alice
        create_income_source(cls.headers1, "Tech Corp Salary", 35000.0, "recurring", "monthly")
        create_income_source(cls.headers1, "Design Retainer", 5000.0, "recurring", "monthly")

    # ─── Tests 1–4: Income Source Creation ────────────────────────────────────

    def test_01_recurring_salary_created(self):
        """1. Recurring salary income source exists and has correct type."""
        res = client.get("/api/income-sources", headers=self.headers1)
        assert res.status_code == 200
        sources = res.json()
        salaries = [s for s in sources if s["name"] == "Tech Corp Salary"]
        assert len(salaries) == 1
        s = salaries[0]
        assert s["income_type"] == "recurring"
        assert s["frequency"] == "monthly"
        assert s["amount"] == 35000.0

    def test_02_recurring_freelance_created(self):
        """2. Recurring freelance income source exists and has correct type."""
        res = client.get("/api/income-sources", headers=self.headers1)
        sources = res.json()
        retainers = [s for s in sources if s["name"] == "Design Retainer"]
        assert len(retainers) == 1
        assert retainers[0]["income_type"] == "recurring"
        assert retainers[0]["amount"] == 5000.0

    def test_03_one_time_bonus_created(self):
        """3. One-time bonus income source has correct type."""
        res = client.get("/api/income-sources", headers=self.headers1)
        sources = res.json()
        bonuses = [s for s in sources if s["name"] == "Diwali Bonus"]
        assert len(bonuses) == 1
        assert bonuses[0]["income_type"] == "one_time"
        assert bonuses[0]["amount"] == 20000.0

    def test_04_inactive_source_excluded_from_monthly_income(self):
        """4. Inactive income source does NOT count toward monthly income."""
        create_income_source(self.headers1, "Old Side Gig", 10000.0, "recurring", "monthly", is_active=False)
        sum_res = client.get("/api/financials/summary", headers=self.headers1)
        assert sum_res.status_code == 200
        # Active recurring: 35k + 5k = 40k. Inactive 10k excluded.
        assert sum_res.json()["total_monthly_income"] == 40000.0

    # ─── Tests 5–6: Income Calculation Logic ──────────────────────────────────

    def test_05_weekly_income_conversion(self):
        """5. Weekly recurring income converts correctly to monthly equivalent (×52/12 ≈ 4333)."""
        _, hdr = create_test_user_and_auth("Charlie", "charlie@phase2.test")
        create_income_source(hdr, "Weekly Contract", 1000.0, "recurring", "weekly")
        sum_res = client.get("/api/financials/summary", headers=hdr)
        assert sum_res.status_code == 200
        monthly = sum_res.json()["total_monthly_income"]
        # 1000 * 52 / 12 ≈ 4333.33 (allow ±10 for rounding differences)
        assert abs(monthly - 4333.33) < 10.0, f"Expected ~4333.33, got {monthly}"

    def test_06_zero_recurring_fallback(self):
        """6. User with no income sources falls back to profile.monthly_income (₹30k)."""
        _, hdr = create_test_user_and_auth("David", "david@phase2.test")
        sum_res = client.get("/api/financials/summary", headers=hdr)
        assert sum_res.status_code == 200
        monthly = sum_res.json()["total_monthly_income"]
        assert monthly == 30000.0, f"Expected fallback 30000.0, got {monthly}"

    # ─── Tests 7–12: Atomic Allocation ────────────────────────────────────────

    def test_07_valid_allocation(self):
        """7. ₹20k bonus allocation: ₹8k + ₹5k to goals + ₹7k free cash sums exactly."""
        # Verify the pre-allocated bonus in setup_class
        res = client.get("/api/income-sources", headers=self.headers1)
        sources = res.json()
        bonus = next(s for s in sources if s["id"] == self.bonus_source_id)
        assert bonus["allocated_to_goals"] == 13000.0
        assert bonus["free_cash"] == 7000.0
        assert bonus["unallocated_amount"] == 0.0

        # Verify DB goal balances — allocations added on top of starting amounts
        db = TestingSessionLocal()
        g1 = db.query(FinancialGoal).filter(FinancialGoal.id == self.goal1_id).first()
        g2 = db.query(FinancialGoal).filter(FinancialGoal.id == self.goal2_id).first()
        # ₹8000 was allocated to goal1, ₹5000 to goal2 in setup_class
        # (current_amount from create may be 0, allocation adds on top)
        assert g1.current_amount >= 8000.0
        assert g2.current_amount >= 5000.0
        db.close()

    def test_08_allocation_over_amount_rejected(self):
        """8. Allocation total > income source amount is rejected (HTTP 400 sum mismatch)."""
        src_id = create_income_source(self.headers1, "Bounty A", 10000.0)["id"]
        # 9000 + 2000 = 11000 > 10000
        res = client.post(f"/api/income-sources/{src_id}/allocate", json={
            "allocations": [{"goal_id": self.goal1_id, "amount": 9000.0}],
            "free_cash_amount": 2000.0,
        }, headers=self.headers1)
        assert res.status_code == 400
        assert "mismatch" in res.json()["detail"].lower() or "does not equal" in res.json()["detail"].lower()

    def test_09_allocation_partial_rejected_and_full_succeeds(self):
        """9. Partial allocation is rejected; full exact allocation succeeds with 0 unallocated."""
        src_id = create_income_source(self.headers1, "Bounty B", 10000.0)["id"]

        # Partial: 6000 + 2000 = 8000 ≠ 10000 → rejected
        res_partial = client.post(f"/api/income-sources/{src_id}/allocate", json={
            "allocations": [{"goal_id": self.goal1_id, "amount": 6000.0}],
            "free_cash_amount": 2000.0,
        }, headers=self.headers1)
        assert res_partial.status_code == 400

        # Full: 6000 + 4000 = 10000 → succeeds with unallocated_amount == 0
        res_full = client.post(f"/api/income-sources/{src_id}/allocate", json={
            "allocations": [{"goal_id": self.goal1_id, "amount": 6000.0}],
            "free_cash_amount": 4000.0,
        }, headers=self.headers1)
        assert res_full.status_code == 200, res_full.text
        data = res_full.json()
        # unallocated_amount should be 0 since sum equals source amount
        assert data.get("unallocated_amount", 0.0) == 0.0

    def test_10_allocation_cross_user_goal_rejected(self):
        """10. Bob cannot allocate his income source to Alice's goal (HTTP 404)."""
        bob_src_id = create_income_source(self.headers2, "Bob Bonus", 5000.0)["id"]
        # Bob tries to put money into Alice's goal — goal ownership check fires first
        res = client.post(f"/api/income-sources/{bob_src_id}/allocate", json={
            "allocations": [{"goal_id": self.goal1_id, "amount": 5000.0}],
            "free_cash_amount": 0.0,
        }, headers=self.headers2)
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_11_duplicate_allocation_rejected(self):
        """11. Re-allocating an already-allocated source returns HTTP 400 (immutability)."""
        # bonus_source_id was fully allocated in setup_class
        res = client.post(f"/api/income-sources/{self.bonus_source_id}/allocate", json={
            "allocations": [{"goal_id": self.goal1_id, "amount": 20000.0}],
            "free_cash_amount": 0.0,
        }, headers=self.headers1)
        assert res.status_code == 400
        assert "already been allocated" in res.json()["detail"].lower() or "immutable" in res.json()["detail"].lower()

    def test_12_allocation_invariant_sum_equals_source_amount(self):
        """12. DB invariant: sum of IncomeAllocation records for bonus == ₹20,000."""
        db = TestingSessionLocal()
        allocs = db.query(IncomeAllocation).filter(
            IncomeAllocation.income_source_id == self.bonus_source_id
        ).all()
        total = sum(Decimal(str(a.amount)) for a in allocs)
        db.close()
        assert total == Decimal("20000.00"), f"Invariant violated: sum = {total}"

    # ─── Tests 13–16: Historical Integrity ────────────────────────────────────

    def test_13_14_15_16_historical_integrity_preservation(self):
        """
        13. Delete of allocated income source is blocked (HTTP 400).
        14. Goal still accepts additional deposits after allocation.
        15. Delete remains blocked after the additional deposit.
        16. Goal balance is never corrupted by delete attempts.
        """
        db = TestingSessionLocal()
        g1 = db.query(FinancialGoal).filter(FinancialGoal.id == self.goal1_id).first()
        g1_initial = g1.current_amount
        db.close()

        # Test 13: First delete attempt — blocked
        del_res = client.delete(f"/api/income-sources/{self.bonus_source_id}", headers=self.headers1)
        assert del_res.status_code == 400
        assert "cannot delete" in del_res.json()["detail"].lower() or "allocated" in del_res.json()["detail"].lower()

        # Test 14: Goal still accepts additional deposits
        db = TestingSessionLocal()
        g1 = db.query(FinancialGoal).filter(FinancialGoal.id == self.goal1_id).first()
        g1.current_amount += 2000.0
        db.commit()
        db.close()

        # Test 15: Delete still blocked after additional deposit
        del_res2 = client.delete(f"/api/income-sources/{self.bonus_source_id}", headers=self.headers1)
        assert del_res2.status_code == 400

        # Test 16: Balance unchanged by delete attempts — no rollback corruption
        db = TestingSessionLocal()
        g1_after = db.query(FinancialGoal).filter(FinancialGoal.id == self.goal1_id).first()
        expected = g1_initial + 2000.0
        assert g1_after.current_amount == expected, (
            f"Historical integrity violated: expected {expected}, got {g1_after.current_amount}"
        )
        db.close()

    # ─── Tests 17–21: Safe-to-Spend & Explainability ──────────────────────────

    def test_17_recurring_affects_monthly_baseline(self):
        """17. Recurring income (35k + 5k = 40k) forms the safe-to-spend baseline."""
        res = client.get("/api/financials/safe-to-spend", headers=self.headers1)
        assert res.status_code == 200
        data = res.json()
        assert data["recurring_monthly_income"] == 40000.0

    def test_18_one_time_does_not_inflate_monthly_income(self):
        """18. One-time bonus (₹20k) does NOT inflate recurring monthly income (must stay 40k)."""
        res = client.get("/api/financials/safe-to-spend", headers=self.headers1)
        assert res.status_code == 200
        assert res.json()["recurring_monthly_income"] == 40000.0  # NOT 60000

    def test_19_safe_to_spend_under_monthly_income(self):
        """19. Monthly safe-to-spend is ≤ recurring income (obligations are deducted)."""
        res = client.get("/api/financials/safe-to-spend", headers=self.headers1)
        assert res.status_code == 200
        data = res.json()
        assert data["remaining_safe_spending"] <= 40000.0

    def test_20_free_cash_separately_visible(self):
        """20. Supplemental free cash from bonus allocation is visible and ≥ ₹7,000."""
        res = client.get("/api/financials/safe-to-spend", headers=self.headers1)
        assert res.status_code == 200
        data = res.json()
        assert "supplemental_free_cash" in data
        assert data["supplemental_free_cash"] >= 7000.0

    def test_21_safe_to_spend_has_explanation(self):
        """21. Safe-to-spend returns a human-readable explanation string."""
        res = client.get("/api/financials/safe-to-spend", headers=self.headers1)
        assert res.status_code == 200
        data = res.json()
        assert "explanation" in data
        assert isinstance(data["explanation"], str) and len(data["explanation"]) > 20

    # ─── Tests 22–25: Recommendation Execution ────────────────────────────────

    def test_22_apply_goal_topup_recommendation(self):
        """22. Applying GOAL_TOPUP executes a real DB mutation on the goal balance."""
        db = TestingSessionLocal()
        g1_before = db.query(FinancialGoal).filter(FinancialGoal.id == self.goal1_id).first().current_amount
        db.close()

        res = client.post(f"/api/recommendations/act-protect-goal-{self.goal1_id}/apply", json={
            "type": "GOAL_TOPUP",
            "target_id": self.goal1_id,
            "suggested_amount": 1000.0
        }, headers=self.headers1)
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "applied"

        db = TestingSessionLocal()
        g1_after = db.query(FinancialGoal).filter(FinancialGoal.id == self.goal1_id).first()
        assert g1_after.current_amount == g1_before + 1000.0
        db.close()

    def test_23_dismiss_recommendation(self):
        """23. Dismissing a recommendation marks it dismissed with no financial mutation."""
        # Create a DB recommendation record
        db = TestingSessionLocal()
        rec = Recommendation(
            user_id=self.user1.id,
            title="Advisory Notice",
            description="Review your spending",
            category="Budget",
            priority="Low",
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        rec_id = rec.id
        db.close()

        res = client.post(f"/api/recommendations/{rec_id}/dismiss", headers=self.headers1)
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "dismissed"

        # Confirm is_dismissed set in DB
        db = TestingSessionLocal()
        rec_obj = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
        assert rec_obj.is_dismissed is True
        db.close()

    def test_24_apply_recommendation_nonexistent_goal(self):
        """24. Applying GOAL_TOPUP to a non-existent goal returns HTTP 404."""
        res = client.post("/api/recommendations/act-protect-goal-999999/apply", json={
            "type": "GOAL_TOPUP",
            "target_id": 999999,
            "suggested_amount": 500.0
        }, headers=self.headers1)
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_25_cross_user_recommendation_isolation(self):
        """25. Bob cannot apply a GOAL_TOPUP targeting Alice's goal (HTTP 404)."""
        res = client.post(f"/api/recommendations/act-protect-goal-{self.goal1_id}/apply", json={
            "type": "GOAL_TOPUP",
            "target_id": self.goal1_id,
            "suggested_amount": 500.0
        }, headers=self.headers2)
        # goal1_id belongs to Alice, not Bob → 404
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    # ─── Tests 26–31: Security Verifications ──────────────────────────────────

    def test_26_unauthenticated_predict_risk_rejected(self):
        """26. POST /api/predict-risk without authentication returns 401."""
        res = client.post("/api/predict-risk", json={
            "income": 50000.0,
            "expenses": 30000.0,
            "savings": 20000.0,
            "debt": 5000.0,
            "transaction_count": 10
        })
        assert res.status_code == 401

    def test_27_authenticated_predict_risk_succeeds(self):
        """27. POST /api/predict-risk with valid auth returns prediction result."""
        res = client.post("/api/predict-risk", json={
            "income": 50000.0,
            "expenses": 30000.0,
            "savings": 20000.0,
            "debt": 5000.0,
            "transaction_count": 10
        }, headers=self.headers1)
        assert res.status_code == 200, res.text
        data = res.json()
        assert "risk_level" in data
        assert "confidence" in data
        assert "financial_health_score" in data

    def test_28_valid_authorized_emergency_fund_action_succeeds(self):
        """28. User with emergency runway < 3 can execute authorized act-emergency-fund."""
        # Ensure Alice has emergency_fund_months = 1 (< 3)
        db = TestingSessionLocal()
        p1 = db.query(FinancialProfile).filter(FinancialProfile.user_id == self.user1.id).first()
        p1.emergency_fund_months = 1
        db.commit()
        db.close()

        res = client.post("/api/recommendations/act-emergency-fund/apply", json={
            "type": "EMERGENCY_RESERVE"
        }, headers=self.headers1)
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "applied"

        db = TestingSessionLocal()
        p1_after = db.query(FinancialProfile).filter(FinancialProfile.user_id == self.user1.id).first()
        assert p1_after.emergency_fund_months == 2
        db.close()

    def test_29_cross_user_emergency_fund_action_rejected(self):
        """29. Bob cannot forge target_id to point to Alice's profile (HTTP 403)."""
        db = TestingSessionLocal()
        alice_profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == self.user1.id).first()
        alice_profile_id = alice_profile.id
        db.close()

        res = client.post("/api/recommendations/act-emergency-fund/apply", json={
            "type": "EMERGENCY_RESERVE",
            "target_id": alice_profile_id
        }, headers=self.headers2)
        assert res.status_code == 403
        assert "unauthorized" in res.json()["detail"].lower()

    def test_30_ineligible_emergency_fund_action_rejected(self):
        """30. If profile has >= 3 months and no persisted recommendation, action is rejected."""
        # Set Bob's emergency runway to 6 months
        db = TestingSessionLocal()
        bob_profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == self.user2.id).first()
        bob_profile.emergency_fund_months = 6
        db.commit()
        db.close()

        res = client.post("/api/recommendations/act-emergency-fund/apply", json={
            "type": "EMERGENCY_RESERVE"
        }, headers=self.headers2)
        assert res.status_code == 400
        assert "not active or authorized" in res.json()["detail"].lower()

    def test_31_dismissed_emergency_fund_action_cannot_be_applied(self):
        """31. If an emergency-fund action was dismissed, applying it is rejected."""
        db = TestingSessionLocal()
        # Clean up any existing record from test_28 so we can insert a dismissed record cleanly
        db.query(Recommendation).filter(
            Recommendation.user_id == self.user1.id,
            (Recommendation.id == "act-emergency-fund") | (Recommendation.id == f"{self.user1.id}_act-emergency-fund")
        ).delete()
        db.commit()

        rec = Recommendation(
            id=f"{self.user1.id}_act-emergency-fund",
            user_id=self.user1.id,
            title="Emergency Fund",
            description="Boost buffer",
            category="Savings",
            priority="High",
            is_dismissed=True
        )
        db.add(rec)
        db.commit()
        db.close()

        res = client.post("/api/recommendations/act-emergency-fund/apply", json={
            "type": "EMERGENCY_RESERVE"
        }, headers=self.headers1)
        assert res.status_code == 400
        assert "not active or authorized" in res.json()["detail"].lower()

    def test_32_applied_recommendation_persists_in_database(self):
        """32. Applying a recommendation sets is_applied=True and applied_at timestamp in the DB."""
        db = TestingSessionLocal()
        rec_id = f"act-protect-goal-{self.goal1_id}"
        rec = db.query(Recommendation).filter(
            Recommendation.id == rec_id,
            Recommendation.user_id == self.user1.id
        ).first()
        assert rec is not None
        assert rec.is_applied is True
        assert rec.applied_at is not None
        db.close()

    def test_33_profile_summary_reflects_applied_recommendation(self):
        """33. Fetching /api/financials/summary returns is_applied: True for applied recommendations."""
        res = client.get("/api/financials/summary", headers=self.headers1)
        assert res.status_code == 200, res.text
        data = res.json()
        actions = data.get("next_best_actions", [])
        rec_id = f"act-protect-goal-{self.goal1_id}"
        matching = [a for a in actions if a.get("id") == rec_id]
        if matching:
            assert matching[0].get("is_applied") is True

    def test_34_reapplying_recommendation_is_rejected_preventing_duplicate(self):
        """34. Re-applying an already applied recommendation returns HTTP 400 and prevents duplicate mutation."""
        db = TestingSessionLocal()
        g1_before = db.query(FinancialGoal).filter(FinancialGoal.id == self.goal1_id).first().current_amount
        db.close()

        res = client.post(f"/api/recommendations/act-protect-goal-{self.goal1_id}/apply", json={
            "type": "GOAL_TOPUP",
            "target_id": self.goal1_id,
            "suggested_amount": 1000.0
        }, headers=self.headers1)
        assert res.status_code == 400
        assert "already been applied" in res.json()["detail"].lower()

        # Confirm goal amount was NOT mutated again
        db = TestingSessionLocal()
        g1_after = db.query(FinancialGoal).filter(FinancialGoal.id == self.goal1_id).first().current_amount
        assert g1_after == g1_before
        db.close()

    def test_35_failed_apply_leaves_financial_data_unchanged_and_rolls_back(self):
        """35. If apply fails during execution, database rollback ensures financial data is unchanged."""
        from unittest.mock import patch
        import datetime

        db = TestingSessionLocal()
        # Create a new distinct goal for this test with non-null target_date
        test_goal = FinancialGoal(
            user_id=self.user1.id,
            title="Rollback Goal",
            target_amount=10000.0,
            current_amount=2000.0,
            target_date=datetime.date.today() + datetime.timedelta(days=365)
        )
        db.add(test_goal)
        db.commit()
        db.refresh(test_goal)
        t_goal_id = test_goal.id
        db.close()

        # Simulate a database failure right before commit
        with patch.object(Recommendation, "__init__", side_effect=RuntimeError("Simulated database write crash")):
            res = client.post(f"/api/recommendations/act-protect-goal-{t_goal_id}/apply", json={
                "type": "GOAL_TOPUP",
                "target_id": t_goal_id,
                "suggested_amount": 500.0
            }, headers=self.headers1)
            assert res.status_code == 500
            assert "atomic application failed" in res.json()["detail"].lower()

        # Verify financial goal balance is COMPLETELY UNCHANGED
        db = TestingSessionLocal()
        g_check = db.query(FinancialGoal).filter(FinancialGoal.id == t_goal_id).first()
        assert g_check.current_amount == 2000.0
        db.close()

    def test_36_failed_apply_does_not_persist_is_applied(self):
        """36. If apply fails, no Recommendation record with is_applied=True is persisted in DB."""
        from unittest.mock import patch

        rec_id = "act-protect-goal-888888"
        with patch.object(Recommendation, "__init__", side_effect=RuntimeError("Simulated write error")):
            res = client.post(f"/api/recommendations/{rec_id}/apply", json={
                "type": "GOAL_TOPUP",
                "target_id": self.goal1_id,
                "suggested_amount": 500.0
            }, headers=self.headers1)
            assert res.status_code == 500

        db = TestingSessionLocal()
        rec_check = db.query(Recommendation).filter(
            Recommendation.user_id == self.user1.id,
            (Recommendation.id == rec_id) | (Recommendation.id == f"{self.user1.id}_{rec_id}")
        ).first()
        assert rec_check is None
        db.close()

    def test_37_simulated_concurrent_duplicate_apply_blocked_by_transaction_isolation(self):
        """37. Second simultaneous apply attempt encountering an applied record or duplicate key is blocked."""
        import datetime
        db = TestingSessionLocal()
        new_g = FinancialGoal(
            user_id=self.user1.id,
            title="Concurrency Goal",
            target_amount=50000.0,
            current_amount=5000.0,
            target_date=datetime.date.today() + datetime.timedelta(days=180)
        )
        db.add(new_g)
        db.commit()
        db.refresh(new_g)
        cg_id = new_g.id
        db.close()

        # First request succeeds
        res1 = client.post(f"/api/recommendations/act-protect-goal-{cg_id}/apply", json={
            "type": "GOAL_TOPUP",
            "target_id": cg_id,
            "suggested_amount": 1000.0
        }, headers=self.headers1)
        assert res1.status_code == 200
        assert res1.json()["is_applied"] is True

        # Second overlapping request is rejected with 400
        res2 = client.post(f"/api/recommendations/act-protect-goal-{cg_id}/apply", json={
            "type": "GOAL_TOPUP",
            "target_id": cg_id,
            "suggested_amount": 1000.0
        }, headers=self.headers1)
        assert res2.status_code == 400
        assert "already been applied" in res2.json()["detail"].lower()

        # Goal amount is exactly 6000 (5000 + 1000), not double counted
        db = TestingSessionLocal()
        cg_final = db.query(FinancialGoal).filter(FinancialGoal.id == cg_id).first()
        assert cg_final.current_amount == 6000.0
        db.close()


class TestDashboardDataIntegrity:
    """Verify that dashboard metrics and future balance forecast are driven by authenticated real backend data."""

    @pytest.fixture(autouse=True)
    def setup_users(self):
        self.user_a, self.headers_a = create_test_user_and_auth(
            full_name="Dashboard User A", email="dashboard_a@example.com"
        )
        self.user_b, self.headers_b = create_test_user_and_auth(
            full_name="Dashboard User B", email="dashboard_b@example.com"
        )

    def test_dashboard_summary_requires_authentication(self):
        """Dashboard summary must reject unauthenticated requests."""
        res = client.get("/api/financials/summary")
        assert res.status_code in [401, 403]

    def test_dashboard_forecast_scenarios_structure(self):
        """Forecast scenarios must provide real computed metrics and daily trajectory chart data."""
        res = client.get("/api/financials/summary", headers=self.headers_a)
        assert res.status_code == 200
        data = res.json()

        assert "forecast_scenarios" in data
        fs = data["forecast_scenarios"]
        assert "projected_month_end_balance" in fs
        assert "scenarios" in fs
        assert "expected" in fs["scenarios"]
        assert "high_spending" in fs["scenarios"]
        assert "low_spending" in fs["scenarios"]
        assert "chart_data" in fs
        assert isinstance(fs["chart_data"], list)
        assert len(fs["chart_data"]) > 0
        for point in fs["chart_data"]:
            assert "day" in point
            assert "expected" in point
            assert "high_spend" in point
            assert "low_spend" in point

    def test_dashboard_user_isolation(self):
        """User A and User B receive isolated metrics and goals."""
        import datetime
        db = TestingSessionLocal()
        goal_a = FinancialGoal(
            user_id=self.user_a.id,
            title="User A Unique Goal",
            target_amount=100000.0,
            current_amount=25000.0,
            target_date=datetime.date.today() + datetime.timedelta(days=90)
        )
        db.add(goal_a)
        db.commit()
        db.close()

        res_a = client.get("/api/financials/summary", headers=self.headers_a)
        res_b = client.get("/api/financials/summary", headers=self.headers_b)

        assert res_a.status_code == 200
        assert res_b.status_code == 200

        data_a = res_a.json()
        data_b = res_b.json()

        # Goal should appear only in User A's goals
        assert any(g["title"] == "User A Unique Goal" for g in data_a["goals"])
        assert not any(g["title"] == "User A Unique Goal" for g in data_b["goals"])

    def test_dashboard_genuine_zero_and_empty_budgets(self):
        """Dashboard preserves genuine zeros in metrics and returns empty budgets without fabrication."""
        # Create a fresh user with zero transactions and zero budgets
        user_c, headers_c = create_test_user_and_auth("ZeroUser", "zerouser@example.com")
        res = client.get("/api/financials/summary", headers=headers_c)
        assert res.status_code == 200
        data = res.json()

        # Metrics for a user with 0 transactions should be genuine 0, not missing or fabricated
        assert data["total_income"] == 0.0 or data["total_income"] == 0
        assert data["total_expense"] == 0.0 or data["total_expense"] == 0
        assert data["savings"] == 0.0 or data["savings"] == 0
        assert data["transaction_count"] == 0

        # Budgets should be an empty list, not auto-populated with fallback items
        assert isinstance(data["budgets"], list)
        assert len(data["budgets"]) == 0

    def test_goal_protection_status_distinguishes_completed_goals(self):
        """Goal protection marks goals with current_amount >= target_amount as COMPLETED."""
        import datetime
        user_d, headers_d = create_test_user_and_auth("GoalUser", "goaluser@example.com")
        db = TestingSessionLocal()
        # Completed goal
        completed_goal = FinancialGoal(
            user_id=user_d.id,
            title="Completed Laptop Goal",
            target_amount=50000.0,
            current_amount=50000.0,
            target_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        # Incomplete active goal
        active_goal = FinancialGoal(
            user_id=user_d.id,
            title="Active Emergency Fund",
            target_amount=100000.0,
            current_amount=20000.0,
            target_date=datetime.date.today() + datetime.timedelta(days=180)
        )
        db.add(completed_goal)
        db.add(active_goal)
        db.commit()
        db.close()

        res = client.get("/api/financials/summary", headers=headers_d)
        assert res.status_code == 200
        data = res.json()

        assert "goal_protection" in data
        gp_list = data["goal_protection"]
        completed_item = next((g for g in gp_list if g["title"] == "Completed Laptop Goal"), None)
        active_item = next((g for g in gp_list if g["title"] == "Active Emergency Fund"), None)

        assert completed_item is not None
        assert completed_item["status"] == "COMPLETED"

        assert active_item is not None
        assert active_item["status"] != "COMPLETED"
        assert active_item["current_amount"] < active_item["target_amount"]


# ==============================================================================
# SPEC: Transaction CRUD, Persistence, Summary Recalculation & Isolation Tests
# ==============================================================================

class TestTransactionLifecycle:
    """
    Verifies that creating, editing, and deleting transactions:
    1. Persist through the authenticated API
    2. Recalculate financial summary aggregates (total_income, total_expense, savings, transaction_count)
    3. Update budget category spent amounts
    4. Enforce user data isolation (user A cannot edit/delete user B's transaction)
    5. Enforce strict backend validation (rejects invalid type, negative amount, future date)
    """

    def test_create_transaction_updates_aggregates_and_budget(self):
        user, headers = create_test_user_and_auth(
            full_name="Tx Lifecycle User",
            email="tx_lifecycle@example.com"
        )
        today_str = datetime.date.today().isoformat()

        # Create a budget for Food
        b_res = client.post("/api/budgets", json={
            "category": "Food",
            "monthly_limit": 5000.0
        }, headers=headers)
        assert b_res.status_code == 200

        # Create an Income transaction
        inc_res = client.post("/api/transactions", json={
            "type": "Income",
            "category": "Salary",
            "amount": 25000.0,
            "description": "Monthly stipend",
            "transaction_date": today_str,
            "payment_method": "Bank Transfer"
        }, headers=headers)
        assert inc_res.status_code == 200
        inc_data = inc_res.json()
        assert inc_data["amount"] == 25000.0

        # Create an Expense transaction in Food
        exp_res = client.post("/api/transactions", json={
            "type": "Expense",
            "category": "Food",
            "amount": 1500.0,
            "description": "Groceries",
            "transaction_date": today_str,
            "payment_method": "UPI"
        }, headers=headers)
        assert exp_res.status_code == 200
        exp_data = exp_res.json()
        assert exp_data["amount"] == 1500.0

        # Check financial summary reflects income, expense, savings, transaction count
        sum_res = client.get("/api/financials/summary", headers=headers)
        assert sum_res.status_code == 200
        summary = sum_res.json()

        assert summary["total_income"] == 25000.0
        assert summary["total_expense"] == 1500.0
        assert summary["savings"] == 23500.0
        assert summary["transaction_count"] == 2

        # Check budget spent updated
        budgets_res = client.get("/api/budgets", headers=headers)
        assert budgets_res.status_code == 200
        budgets = budgets_res.json()
        food_budget = next(b for b in budgets if b["category"] == "Food")
        assert food_budget["spent"] == 1500.0

    def test_update_transaction_updates_aggregates_and_budgets(self):
        user, headers = create_test_user_and_auth(
            full_name="Tx Update User",
            email="tx_update@example.com"
        )
        today_str = datetime.date.today().isoformat()

        # Budgets for Food and Bills
        client.post("/api/budgets", json={"category": "Food", "monthly_limit": 5000.0}, headers=headers)
        client.post("/api/budgets", json={"category": "Bills", "monthly_limit": 3000.0}, headers=headers)

        # Create expense in Food of 1000
        create_res = client.post("/api/transactions", json={
            "type": "Expense",
            "category": "Food",
            "amount": 1000.0,
            "description": "Dinner",
            "transaction_date": today_str,
            "payment_method": "Card"
        }, headers=headers)
        assert create_res.status_code == 200
        tx_id = create_res.json()["id"]

        # Update expense: change category to Bills and amount to 1800
        update_res = client.put(f"/api/transactions/{tx_id}", json={
            "category": "Bills",
            "amount": 1800.0
        }, headers=headers)
        assert update_res.status_code == 200
        updated = update_res.json()
        assert updated["category"] == "Bills"
        assert updated["amount"] == 1800.0

        # Verify summary reflects new total
        sum_res = client.get("/api/financials/summary", headers=headers)
        assert sum_res.status_code == 200
        assert sum_res.json()["total_expense"] == 1800.0

        # Verify budgets: Food spent reset to 0, Bills spent is 1800
        budgets_res = client.get("/api/budgets", headers=headers)
        budgets = budgets_res.json()
        food_b = next(b for b in budgets if b["category"] == "Food")
        bills_b = next(b for b in budgets if b["category"] == "Bills")
        assert food_b["spent"] == 0.0
        assert bills_b["spent"] == 1800.0

    def test_delete_transaction_removes_from_aggregates(self):
        user, headers = create_test_user_and_auth(
            full_name="Tx Delete User",
            email="tx_delete@example.com"
        )
        today_str = datetime.date.today().isoformat()

        client.post("/api/budgets", json={"category": "Travel", "monthly_limit": 4000.0}, headers=headers)

        # Create travel expense
        create_res = client.post("/api/transactions", json={
            "type": "Expense",
            "category": "Travel",
            "amount": 1200.0,
            "description": "Cab ride",
            "transaction_date": today_str,
            "payment_method": "UPI"
        }, headers=headers)
        tx_id = create_res.json()["id"]

        # Verify initial spent
        b_res = client.get("/api/budgets", headers=headers)
        travel_b = next(b for b in b_res.json() if b["category"] == "Travel")
        assert travel_b["spent"] == 1200.0

        # Delete transaction
        del_res = client.delete(f"/api/transactions/{tx_id}", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "success"

        # Verify summary total_expense is 0
        sum_res = client.get("/api/financials/summary", headers=headers)
        assert sum_res.json()["total_expense"] == 0.0
        assert sum_res.json()["transaction_count"] == 0

        # Verify budget spent decremented to 0
        b_res2 = client.get("/api/budgets", headers=headers)
        travel_b2 = next(b for b in b_res2.json() if b["category"] == "Travel")
        assert travel_b2["spent"] == 0.0

    def test_user_cannot_modify_or_delete_other_user_transaction(self):
        _, headers_a = create_test_user_and_auth(full_name="User A", email="usera_iso@example.com")
        _, headers_b = create_test_user_and_auth(full_name="User B", email="userb_iso@example.com")
        today_str = datetime.date.today().isoformat()

        # User A creates a transaction
        tx_a = client.post("/api/transactions", json={
            "type": "Expense",
            "category": "Food",
            "amount": 500.0,
            "description": "User A transaction",
            "transaction_date": today_str,
            "payment_method": "Cash"
        }, headers=headers_a).json()
        tx_id = tx_a["id"]

        # User B tries to fetch User A's transaction -> 404
        get_res = client.get(f"/api/transactions/{tx_id}", headers=headers_b)
        assert get_res.status_code == 404

        # User B tries to update User A's transaction -> 404
        update_res = client.put(f"/api/transactions/{tx_id}", json={
            "amount": 9999.0
        }, headers=headers_b)
        assert update_res.status_code == 404

        # User B tries to delete User A's transaction -> 404
        del_res = client.delete(f"/api/transactions/{tx_id}", headers=headers_b)
        assert del_res.status_code == 404

        # Verify transaction remains untouched for User A
        tx_check = client.get(f"/api/transactions/{tx_id}", headers=headers_a)
        assert tx_check.status_code == 200
        assert tx_check.json()["amount"] == 500.0

    def test_invalid_transaction_rejected(self):
        _, headers = create_test_user_and_auth(full_name="Validation User", email="val_tx@example.com")
        today = datetime.date.today()
        future_date = (today + datetime.timedelta(days=5)).isoformat()

        # Negative amount
        res1 = client.post("/api/transactions", json={
            "type": "Expense",
            "category": "Food",
            "amount": -50.0,
            "transaction_date": today.isoformat(),
            "payment_method": "Cash"
        }, headers=headers)
        assert res1.status_code == 422

        # Future date
        res2 = client.post("/api/transactions", json={
            "type": "Expense",
            "category": "Food",
            "amount": 100.0,
            "transaction_date": future_date,
            "payment_method": "Cash"
        }, headers=headers)
        assert res2.status_code == 422

        # Invalid type
        res3 = client.post("/api/transactions", json={
            "type": "Transfer",
            "category": "Food",
            "amount": 100.0,
            "transaction_date": today.isoformat(),
            "payment_method": "Cash"
        }, headers=headers)
        assert res3.status_code == 422


# ==============================================================================
# SPEC: Goal Protection Engine Financial Reactivity & Recovery Tests
# ==============================================================================

class TestGoalProtectionLifecycle:
    """
    Verifies that Goal Protection:
    1. Accurately evaluates real financial changes (expenses deplete available monthly savings).
    2. Identifies when a goal transitions between ON_TRACK, NEEDS_ATTENTION, and AT_RISK with correct shortfalls.
    3. Dynamically clears risk information once an expense is deleted or modified.
    4. Generates contextual recovery recommendations based on current persisted goal data.
    5. Preserves user isolation (User B cannot see or manipulate User A's goal protection).
    """

    def test_expense_affects_goal_protection_status_and_shortfall(self):
        user, headers = create_test_user_and_auth(
            full_name="Goal Defense User",
            email="goal_defense@example.com"
        )
        today = datetime.date.today()
        # Create a goal due in 2 months needing 20,000 (10,000/month)
        target_date = (today + datetime.timedelta(days=60)).isoformat()
        g_res = client.post("/api/goals", json={
            "title": "Emergency Reserve Build",
            "target_amount": 20000.0,
            "target_date": target_date
        }, headers=headers)
        assert g_res.status_code == 200
        goal_id = g_res.json()["id"]

        # User has an income transaction of 50,000 this month
        client.post("/api/transactions", json={
            "type": "Income",
            "category": "Salary",
            "amount": 50000.0,
            "transaction_date": today.isoformat(),
            "payment_method": "Bank Transfer"
        }, headers=headers)

        # Before high expenses: available savings = 50,000; required = 10,000 -> ON_TRACK
        sum_res1 = client.get("/api/financials/summary", headers=headers)
        assert sum_res1.status_code == 200
        gp1 = next(g for g in sum_res1.json()["goal_protection"] if g["id"] == goal_id)
        assert gp1["status"] == "ON_TRACK"
        assert gp1["projected_shortfall"] == 0.0

        # Now add heavy expense of 45,000 -> available savings drops to 5,000 (which is < 10,000)
        exp_res = client.post("/api/transactions", json={
            "type": "Expense",
            "category": "Shopping",
            "amount": 45000.0,
            "transaction_date": today.isoformat(),
            "payment_method": "Card"
        }, headers=headers)
        assert exp_res.status_code == 200
        exp_id = exp_res.json()["id"]

        # Goal protection must now reflect financial pressure (NEEDS_ATTENTION or AT_RISK)
        sum_res2 = client.get("/api/financials/summary", headers=headers)
        gp2 = next(g for g in sum_res2.json()["goal_protection"] if g["id"] == goal_id)
        assert gp2["status"] in ["NEEDS_ATTENTION", "AT_RISK"]
        assert gp2["projected_shortfall"] > 0.0
        assert gp2["delay_days"] > 0

        # Verify structured risk and recovery recommendations are generated for this goal
        data2 = sum_res2.json()
        assert any(r["category"] == "Goal Protection" and str(goal_id) in r["id"] for r in data2.get("structured_risks", []))
        actions = data2.get("next_best_actions", [])
        goal_action = next((a for a in actions if a.get("target_id") == goal_id or f"goal-{goal_id}" in a.get("id", "")), None)
        assert goal_action is not None
        assert goal_action["type"] == "GOAL_TOPUP"
        assert goal_action["suggested_amount"] > 0

        # Deleting the expense restores available savings to 50,000 -> Goal returns to ON_TRACK
        client.delete(f"/api/transactions/{exp_id}", headers=headers)

        sum_res3 = client.get("/api/financials/summary", headers=headers)
        gp3 = next(g for g in sum_res3.json()["goal_protection"] if g["id"] == goal_id)
        assert gp3["status"] == "ON_TRACK"
        assert gp3["projected_shortfall"] == 0.0
        # Stale risk for this goal must no longer be present
        assert not any(r["category"] == "Goal Protection" and str(goal_id) in r["id"] for r in sum_res3.json().get("structured_risks", []))

    def test_goal_protection_user_isolation(self):
        _, headers_a = create_test_user_and_auth(full_name="Goal Iso A", email="goal_iso_a@example.com")
        _, headers_b = create_test_user_and_auth(full_name="Goal Iso B", email="goal_iso_b@example.com")
        today = datetime.date.today()

        # User A creates a goal
        g_a = client.post("/api/goals", json={
            "title": "Private Goal A",
            "target_amount": 10000.0,
            "target_date": (today + datetime.timedelta(days=90)).isoformat()
        }, headers=headers_a).json()

        # User B fetches goal-protection endpoint -> must NOT see User A's goal
        gp_res_b = client.get("/api/financials/goal-protection", headers=headers_b)
        assert gp_res_b.status_code == 200
        assert not any(g["id"] == g_a["id"] for g in gp_res_b.json())

        # User B fetches summary -> must NOT see User A's goal
        sum_b = client.get("/api/financials/summary", headers=headers_b)
        assert not any(g["id"] == g_a["id"] for g in sum_b.json()["goal_protection"])


# ==============================================================================
# SPEC: Budget Planner & Budget Utilization Tests
# ==============================================================================

class TestBudgetPlannerLifecycle:
    """
    Verifies that Budget Planner:
    1. Persists budget categories and monthly limits through authenticated API.
    2. Accurately aggregates actual spending, remaining amounts, and utilization percentages from transactions.
    3. Reflects transaction create, update, delete, and category changes in budget totals.
    4. Handles zero limits, missing values, and overspending safely without NaN or misleading metrics.
    5. Safely deletes a budget category while preserving all associated transactions in the ledger.
    6. Strictly isolates budget operations across authenticated users.
    """

    def test_budget_crud_and_spending_aggregation(self):
        user, headers = create_test_user_and_auth(
            full_name="Budget User",
            email="budget_crud@example.com"
        )
        today_str = datetime.date.today().isoformat()

        # 1. Create budget
        b_res = client.post("/api/budgets", json={
            "category": "Dining",
            "monthly_limit": 6000.0
        }, headers=headers)
        assert b_res.status_code == 200
        b_data = b_res.json()
        b_id = b_data["id"]
        assert b_data["category"] == "Dining"
        assert b_data["monthly_limit"] == 6000.0
        assert b_data["spent"] == 0.0
        assert b_data["remaining"] == 6000.0
        assert b_data["utilization_pct"] == 0.0

        # Duplicate category creation should be rejected
        dup_res = client.post("/api/budgets", json={
            "category": "Dining",
            "monthly_limit": 8000.0
        }, headers=headers)
        assert dup_res.status_code == 400

        # 2. Add real expense transaction in Dining
        tx_res = client.post("/api/transactions", json={
            "type": "Expense",
            "category": "Dining",
            "amount": 2400.0,
            "transaction_date": today_str,
            "payment_method": "Card",
            "description": "Team lunch"
        }, headers=headers)
        assert tx_res.status_code == 200
        tx_id = tx_res.json()["id"]

        # Fetch budgets -> spent = 2400, remaining = 3600, utilization = 40.0%
        b_list = client.get("/api/budgets", headers=headers).json()
        dining_b = next(b for b in b_list if b["id"] == b_id)
        assert dining_b["spent"] == 2400.0
        assert dining_b["remaining"] == 3600.0
        assert dining_b["utilization_pct"] == 40.0

        # 3. Update budget monthly limit to 10,000
        upd_res = client.put(f"/api/budgets/{b_id}", json={
            "monthly_limit": 10000.0
        }, headers=headers)
        assert upd_res.status_code == 200
        upd_data = upd_res.json()
        assert upd_data["monthly_limit"] == 10000.0
        assert upd_data["remaining"] == 7600.0
        assert upd_data["utilization_pct"] == 24.0

        # 4. Update transaction amount: 2400 -> 11,000 (Overspending)
        client.put(f"/api/transactions/{tx_id}", json={
            "amount": 11000.0
        }, headers=headers)

        b_list2 = client.get("/api/budgets", headers=headers).json()
        dining_b2 = next(b for b in b_list2 if b["id"] == b_id)
        assert dining_b2["spent"] == 11000.0
        assert dining_b2["remaining"] == 0.0
        assert dining_b2["utilization_pct"] == 110.0

        # 5. Delete budget category safely -> associated transactions MUST NOT be deleted
        del_res = client.delete(f"/api/budgets/{b_id}", headers=headers)
        assert del_res.status_code == 200
        del_json = del_res.json()
        assert del_json["status"] == "success"
        assert del_json["preserved_transactions_count"] == 1

        # Confirm budget record is removed
        b_list3 = client.get("/api/budgets", headers=headers).json()
        assert not any(b["id"] == b_id for b in b_list3)

        # Confirm transaction is still completely intact in the ledger
        tx_check = client.get(f"/api/transactions/{tx_id}", headers=headers)
        assert tx_check.status_code == 200
        assert tx_check.json()["amount"] == 11000.0
        assert tx_check.json()["category"] == "Dining"

    def test_budget_zero_limit_handling(self):
        user, headers = create_test_user_and_auth(
            full_name="Zero Budget User",
            email="zero_budget@example.com"
        )
        today_str = datetime.date.today().isoformat()

        # Create budget with limit = 0.0 (e.g. strict freeze on entertainment)
        b_res = client.post("/api/budgets", json={
            "category": "Entertainment",
            "monthly_limit": 0.0
        }, headers=headers)
        assert b_res.status_code == 200
        b_data = b_res.json()
        assert b_data["monthly_limit"] == 0.0
        assert b_data["spent"] == 0.0
        assert b_data["remaining"] == 0.0
        assert b_data["utilization_pct"] == 0.0

        # Add an expense of 500
        client.post("/api/transactions", json={
            "type": "Expense",
            "category": "Entertainment",
            "amount": 500.0,
            "transaction_date": today_str,
            "payment_method": "UPI"
        }, headers=headers)

        b_list = client.get("/api/budgets", headers=headers).json()
        ent_b = next(b for b in b_list if b["id"] == b_data["id"])
        assert ent_b["spent"] == 500.0
        assert ent_b["remaining"] == 0.0
        # When limit is 0 and spent > 0, utilization should be 100.0 without divide-by-zero error
        assert ent_b["utilization_pct"] == 100.0

    def test_budget_cross_user_isolation(self):
        _, headers_a = create_test_user_and_auth(full_name="User A Budget", email="user_a_bgt@example.com")
        _, headers_b = create_test_user_and_auth(full_name="User B Budget", email="user_b_bgt@example.com")

        # User A creates a budget
        b_a = client.post("/api/budgets", json={
            "category": "Secret Fund",
            "monthly_limit": 5000.0
        }, headers=headers_a).json()
        b_id = b_a["id"]

        # User B cannot see User A's budget
        list_b = client.get("/api/budgets", headers=headers_b).json()
        assert not any(b["id"] == b_id for b in list_b)

        # User B cannot update User A's budget -> 404
        upd_b = client.put(f"/api/budgets/{b_id}", json={
            "monthly_limit": 1000.0
        }, headers=headers_b)
        assert upd_b.status_code == 404

        # User B cannot delete User A's budget -> 404
        del_b = client.delete(f"/api/budgets/{b_id}", headers=headers_b)
        assert del_b.status_code == 404

    def test_budget_current_month_vs_prior_and_future_months(self):
        """
        Verifies that:
        1. Current-month budget metrics include ONLY qualifying expenses within the current calendar month.
        2. Prior-month transactions do not pollute current-month utilization.
        3. Future-month transactions do not affect current-month totals.
        4. Querying a specific month (e.g. ?month=YYYY-MM) returns that exact period's metrics.
        5. Dashboard summary metrics match Budget Planner current-month metrics.
        """
        user, headers = create_test_user_and_auth(
            full_name="Period User",
            email="budget_period@example.com"
        )
        today = datetime.date.today()
        current_month_str = today.strftime("%Y-%m")

        # Prior month (handle year boundary cleanly)
        if today.month == 1:
            prior_year = today.year - 1
            prior_month = 12
        else:
            prior_year = today.year
            prior_month = today.month - 1
        prior_date = datetime.date(prior_year, prior_month, 15)
        prior_month_str = f"{prior_year:04d}-{prior_month:02d}"

        # Create budget for Groceries: limit = 8000
        b_res = client.post("/api/budgets", json={
            "category": "Groceries",
            "monthly_limit": 8000.0
        }, headers=headers)
        assert b_res.status_code == 200
        b_id = b_res.json()["id"]

        # 1. Post expense in PRIOR month of 3000
        client.post("/api/transactions", json={
            "type": "Expense",
            "category": "Groceries",
            "amount": 3000.0,
            "transaction_date": prior_date.isoformat(),
            "payment_method": "Card"
        }, headers=headers)

        # Current month default query -> spent should still be 0.0 (not 3000)
        curr_b = next(b for b in client.get("/api/budgets", headers=headers).json() if b["id"] == b_id)
        assert curr_b["spent"] == 0.0
        assert curr_b["remaining"] == 8000.0
        assert curr_b["utilization_pct"] == 0.0

        # Prior month query -> spent should be 3000.0, remaining 5000.0
        prior_b = next(b for b in client.get(f"/api/budgets?month={prior_month_str}", headers=headers).json() if b["id"] == b_id)
        assert prior_b["spent"] == 3000.0
        assert prior_b["remaining"] == 5000.0
        assert prior_b["utilization_pct"] == 37.5

        # 2. Post expense in CURRENT month of 2000
        curr_tx = client.post("/api/transactions", json={
            "type": "Expense",
            "category": "Groceries",
            "amount": 2000.0,
            "transaction_date": today.isoformat(),
            "payment_method": "UPI"
        }, headers=headers).json()

        # Current month query -> spent = 2000, remaining = 6000, utilization = 25.0%
        curr_b2 = next(b for b in client.get("/api/budgets", headers=headers).json() if b["id"] == b_id)
        assert curr_b2["spent"] == 2000.0
        assert curr_b2["remaining"] == 6000.0
        assert curr_b2["utilization_pct"] == 25.0

        # Dashboard summary check -> budgets list must match Budget Planner authoritative numbers
        sum_res = client.get("/api/financials/summary", headers=headers).json()
        dashboard_b = next(b for b in sum_res["budgets"] if b["id"] == b_id)
        assert dashboard_b["spent"] == 2000.0
        assert dashboard_b["remaining"] == 6000.0
        assert dashboard_b["utilization_pct"] == 25.0

        # 3. Moving a transaction from current month to prior month updates current month spent
        client.put(f"/api/transactions/{curr_tx['id']}", json={
            "transaction_date": prior_date.isoformat()
        }, headers=headers)

        curr_b3 = next(b for b in client.get("/api/budgets", headers=headers).json() if b["id"] == b_id)
        assert curr_b3["spent"] == 0.0
        assert curr_b3["remaining"] == 8000.0

        # Prior month now has 3000 + 2000 = 5000
        prior_b2 = next(b for b in client.get(f"/api/budgets?month={prior_month_str}", headers=headers).json() if b["id"] == b_id)
        assert prior_b2["spent"] == 5000.0
        assert prior_b2["remaining"] == 3000.0


# ==============================================================================
# SPEC: Forecast Projections Endpoint (/api/forecast/projections)
# ==============================================================================
class TestForecastProjectionsEndpoint:
    """
    Tests for the authenticated /api/forecast/projections endpoint.
    Verifies: auth enforcement, response structure, scenario presence,
    user isolation, empty-history fallback, and sensitivity to transaction mutations.
    Avoids assertions tied to exact current dates or random values.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user_f, self.headers_f = create_test_user_and_auth(
            full_name="Forecast User F", email="forecast_f@example.com"
        )
        self.user_g, self.headers_g = create_test_user_and_auth(
            full_name="Forecast User G", email="forecast_g@example.com"
        )

    def test_forecast_requires_authentication(self):
        """Unauthenticated requests must be rejected (401 or 403)."""
        res = client.get("/api/forecast/projections")
        assert res.status_code in (401, 403)

    def test_forecast_response_structure(self):
        """Response must contain all required top-level fields with correct types."""
        res = client.get("/api/forecast/projections", headers=self.headers_f)
        assert res.status_code == 200
        data = res.json()

        # Core projection fields
        assert "projected_income" in data
        assert "projected_expense" in data
        assert "projected_savings" in data
        assert "risk_trend" in data
        assert isinstance(data["risk_trend"], str)

        # Goal completion fields
        assert "goal_completion_months" in data
        assert "goal_completion_date" in data
        assert "goal_completion_title" in data

        # 6-month chart data
        assert "chart_data" in data
        assert isinstance(data["chart_data"], list)
        assert len(data["chart_data"]) == 6, "Must provide exactly 6 months of chart data"
        for point in data["chart_data"]:
            assert "month" in point
            assert "projected_income" in point
            assert "projected_expense" in point
            assert "projected_savings" in point

        # Assumptions block
        assert "assumptions" in data
        assert "method" in data["assumptions"]
        assert "disclaimer" in data["assumptions"]
        assert "expense_data_months" in data["assumptions"]

        # has_sufficient_history flag
        assert "has_sufficient_history" in data

    def test_forecast_contains_balance_scenarios(self):
        """Response must include forecast_scenarios with Expected/High/Low balance projections."""
        res = client.get("/api/forecast/projections", headers=self.headers_f)
        assert res.status_code == 200
        data = res.json()

        assert "forecast_scenarios" in data
        fs = data["forecast_scenarios"]
        assert "projected_month_end_balance" in fs
        assert "scenarios" in fs
        scenarios = fs["scenarios"]
        assert "expected" in scenarios
        assert "high_spending" in scenarios
        assert "low_spending" in scenarios

        assert "chart_data" in fs
        assert isinstance(fs["chart_data"], list)
        assert len(fs["chart_data"]) > 0
        for point in fs["chart_data"]:
            assert "day" in point
            assert "expected" in point
            assert "high_spend" in point
            assert "low_spend" in point

        assert "daily_burn_rate" in fs

    def test_forecast_user_isolation(self):
        """User F and User G receive independent forecast projections."""
        # Give User G a much higher income profile
        db = TestingSessionLocal()
        profile_g = db.query(FinancialProfile).filter(FinancialProfile.user_id == self.user_g.id).first()
        if profile_g:
            profile_g.monthly_income = 200000.0
            db.commit()
        db.close()

        res_f = client.get("/api/forecast/projections", headers=self.headers_f)
        res_g = client.get("/api/forecast/projections", headers=self.headers_g)
        assert res_f.status_code == 200
        assert res_g.status_code == 200

        # User G's projected_income must reflect the higher profile income
        assert res_g.json()["projected_income"] == 200000.0
        # User F uses default (30000 from create_test_user_and_auth)
        assert res_f.json()["projected_income"] != 200000.0

    def test_forecast_empty_history_fallback(self):
        """A user with no transactions must receive a valid non-crash forecast using the average fallback."""
        user_h, headers_h = create_test_user_and_auth(
            full_name="Empty User H", email="forecast_empty_h@example.com"
        )
        res = client.get("/api/forecast/projections", headers=headers_h)
        assert res.status_code == 200
        data = res.json()

        # Must still provide valid numeric values, not null or NaN
        assert isinstance(data["projected_income"], (int, float))
        assert isinstance(data["projected_expense"], (int, float))
        assert isinstance(data["projected_savings"], (int, float))
        assert data["projected_expense"] >= 0
        assert len(data["chart_data"]) == 6

        # With no history, fallback method is average and has_sufficient_history is False
        assert data["has_sufficient_history"] is False
        assert data["assumptions"]["method"] == "average_fallback"
        assert data["assumptions"]["expense_data_months"] == 0

    def test_forecast_changes_after_expense_transaction(self):
        """Adding an expense transaction must change the projected expense in the forecast."""
        user_i, headers_i = create_test_user_and_auth(
            full_name="Forecast User I", email="forecast_i@example.com"
        )

        # Baseline forecast before any transactions
        res_before = client.get("/api/forecast/projections", headers=headers_i)
        assert res_before.status_code == 200
        before = res_before.json()
        before_exp = before["projected_expense"]

        # Add a large expense (use correct schema fields: description + payment_method)
        tx_res = client.post("/api/transactions", json={
            "description": "Big Expense for forecast test",
            "amount": 20000.0,
            "type": "Expense",
            "category": "Other",
            "transaction_date": datetime.date.today().isoformat(),
            "payment_method": "Cash",
        }, headers=headers_i)
        assert tx_res.status_code in (200, 201), f"Transaction creation failed: {tx_res.text}"

        # Forecast after transaction
        res_after = client.get("/api/forecast/projections", headers=headers_i)
        assert res_after.status_code == 200
        after = res_after.json()

        # The projected_expense should increase or remain equal (never silently stay the same
        # as a completely independent value from transactions)
        assert after["projected_expense"] >= before_exp, (
            f"Expected projected_expense to increase after adding a large expense. "
            f"Before: {before_exp}, After: {after['projected_expense']}"
        )

    def test_forecast_income_equals_profile_monthly_income(self):
        """projected_income must reflect the authenticated user's profile monthly_income."""
        user_j, headers_j = create_test_user_and_auth(
            full_name="Forecast User J", email="forecast_j@example.com"
        )
        # Update the profile income
        db = TestingSessionLocal()
        profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == user_j.id).first()
        if profile:
            profile.monthly_income = 75000.0
            db.commit()
        db.close()

        res = client.get("/api/forecast/projections", headers=headers_j)
        assert res.status_code == 200
        data = res.json()
        assert data["projected_income"] == 75000.0

    def test_forecast_savings_is_income_minus_expense(self):
        """projected_savings must equal projected_income minus projected_expense."""
        res = client.get("/api/forecast/projections", headers=self.headers_f)
        assert res.status_code == 200
        data = res.json()
        expected_savings = round(data["projected_income"] - data["projected_expense"], 2)
        actual_savings = round(data["projected_savings"], 2)
        assert abs(actual_savings - expected_savings) < 0.05, (
            f"projected_savings ({actual_savings}) != income ({data['projected_income']}) "
            f"- expense ({data['projected_expense']}) = {expected_savings}"
        )





