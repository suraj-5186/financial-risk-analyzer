"""
Automated Test Suite for FinRisk AI — Password Reset System
Covers all security, functional, edge-case, and regression requirements.
"""
import os
import sys
import hashlib
import datetime
from unittest.mock import patch

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_FILE = os.path.join(backend_dir, "test_password_reset.db")
if os.path.exists(TEST_DB_FILE):
    os.remove(TEST_DB_FILE)

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE}"

from main import app
from models.base import Base
from database.session import get_db
from models.user import User
from models.password_reset import PasswordResetToken
from services.auth_service import hash_password, create_refresh_token
from services.email_service import email_service

# Separate engine for test suite
engine = create_engine(f"sqlite:///{TEST_DB_FILE}", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

Base.metadata.create_all(bind=engine)
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True, scope="module")
def setup_password_reset_env():
    """Ensure tables exist and clean up overrides when done."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass


class TestPasswordResetSuite:
    """Complete End-to-End Password Reset Verification."""

    USER_EMAIL = "reset_tester@example.com"
    OLD_PASSWORD = "OldPassword123!"
    NEW_PASSWORD = "BrandNewPassword456!"

    def _ensure_user(self):
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == self.USER_EMAIL).first()
        if not user:
            user = User(
                email=self.USER_EMAIL,
                full_name="Reset Tester",
                hashed_password=hash_password(self.OLD_PASSWORD)
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        db.close()
        return user

    def test_01_existing_user_requests_reset(self):
        """Case 1: Existing user requests a password reset and receives generic success."""
        self._ensure_user()

        captured_tokens = []
        with patch.object(email_service, "send_password_reset_email", side_effect=lambda *a, **kw: captured_tokens.append(kw.get("reset_token") or a[1]) or True):
            res = client.post("/api/auth/forgot-password", json={"email": self.USER_EMAIL})

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "If that email address is registered" in data["message"]
        assert len(captured_tokens) == 1

    def test_02_non_existing_email_receives_identical_response(self):
        """Case 2: Non-existing email receives the same generic response (anti-enumeration)."""
        res_existing = client.post("/api/auth/forgot-password", json={"email": self.USER_EMAIL})
        res_unknown = client.post("/api/auth/forgot-password", json={"email": "nobody_exists_12345@unknown.com"})

        assert res_unknown.status_code == 200
        assert res_unknown.json()["status"] == res_existing.json()["status"]
        assert res_unknown.json()["message"] == res_existing.json()["message"]

    def test_03_reset_token_not_exposed_in_api_response(self):
        """Case 3: Ensure reset token is never exposed in response body or headers."""
        res = client.post("/api/auth/forgot-password", json={"email": self.USER_EMAIL})
        assert res.status_code == 200
        body_text = res.text.lower()
        assert "token" not in res.json()
        assert "reset_token" not in body_text
        assert "token_hash" not in body_text

    def test_04_token_stored_hashed_in_database(self):
        """Case 4: The database must store only the SHA-256 hash of the token, never plaintext."""
        self._ensure_user()
        captured_tokens = []

        # Clear previous tokens to test fresh generation
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == self.USER_EMAIL).first()
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
        db.commit()

        with patch.object(email_service, "send_password_reset_email", side_effect=lambda *a, **kw: captured_tokens.append(kw.get("reset_token") or a[1]) or True):
            res = client.post("/api/auth/forgot-password", json={"email": self.USER_EMAIL})

        assert res.status_code == 200
        assert len(captured_tokens) == 1
        raw_token = captured_tokens[0]

        # Verify DB entry
        token_record = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).first()
        assert token_record is not None
        assert token_record.token_hash != raw_token
        # Expected SHA-256 hex digest length is 64 characters
        assert len(token_record.token_hash) == 64
        assert token_record.token_hash == hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        assert token_record.is_used is False
        assert token_record.is_revoked is False
        db.close()

    def test_05_valid_token_successfully_resets_password(self):
        """Case 5: A valid token successfully resets the password."""
        self._ensure_user()
        captured_tokens = []

        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == self.USER_EMAIL).first()
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
        db.commit()

        with patch.object(email_service, "send_password_reset_email", side_effect=lambda *a, **kw: captured_tokens.append(kw.get("reset_token") or a[1]) or True):
            client.post("/api/auth/forgot-password", json={"email": self.USER_EMAIL})

        raw_token = captured_tokens[0]

        # First verify token via GET /api/auth/verify-reset-token
        verify_res = client.get(f"/api/auth/verify-reset-token?token={raw_token}")
        assert verify_res.status_code == 200
        assert verify_res.json()["status"] == "valid"

        # Submit new password
        reset_res = client.post("/api/auth/reset-password", json={
            "token": raw_token,
            "new_password": self.NEW_PASSWORD
        })
        assert reset_res.status_code == 200
        assert reset_res.json()["status"] == "success"
        db.close()

    def test_06_new_password_hashed_not_plaintext(self):
        """Case 6: New password is saved as a bcrypt hash, never plaintext."""
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == self.USER_EMAIL).first()
        assert user.hashed_password != self.NEW_PASSWORD
        assert user.hashed_password.startswith("$2b$") or user.hashed_password.startswith("$2a$")
        assert user.password_changed_at is not None
        db.close()

    def test_07_old_password_no_longer_works(self):
        """Case 7: Old password must be rejected by login endpoint."""
        login_res = client.post("/api/login", json={
            "email": self.USER_EMAIL,
            "password": self.OLD_PASSWORD
        })
        assert login_res.status_code == 401
        assert "Invalid email or password" in login_res.json()["detail"]

    def test_08_new_password_works_in_login(self):
        """Case 8: User can log in with the new password and obtain tokens."""
        login_res = client.post("/api/login", json={
            "email": self.USER_EMAIL,
            "password": self.NEW_PASSWORD
        })
        assert login_res.status_code == 200
        data = login_res.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_09_invalid_token_is_rejected(self):
        """Case 9: Bogus or tampered tokens are rejected."""
        res = client.post("/api/auth/reset-password", json={
            "token": "completely_fake_invalid_token_xyz123",
            "new_password": "AnotherNewPassword999!"
        })
        assert res.status_code == 400
        assert "Invalid or unrecognized" in res.json()["detail"]

    def test_10_expired_token_is_rejected(self):
        """Case 10: Tokens past their expiration time are rejected."""
        self._ensure_user()
        captured_tokens = []
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == self.USER_EMAIL).first()
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
        db.commit()

        with patch.object(email_service, "send_password_reset_email", side_effect=lambda *a, **kw: captured_tokens.append(kw.get("reset_token") or a[1]) or True):
            client.post("/api/auth/forgot-password", json={"email": self.USER_EMAIL})

        raw_token = captured_tokens[0]

        # Artificially expire the token in database
        token_record = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).first()
        token_record.expires_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
        db.commit()
        db.close()

        # Check verify endpoint
        verify_res = client.get(f"/api/auth/verify-reset-token?token={raw_token}")
        assert verify_res.status_code == 400
        assert "expired" in verify_res.json()["detail"]

        # Check reset endpoint
        res = client.post("/api/auth/reset-password", json={
            "token": raw_token,
            "new_password": "NewPassword789!"
        })
        assert res.status_code == 400
        assert "expired" in res.json()["detail"]

    def test_11_reused_token_is_rejected(self):
        """Case 11: A token cannot be used a second time."""
        self._ensure_user()
        captured_tokens = []
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == self.USER_EMAIL).first()
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
        db.commit()

        with patch.object(email_service, "send_password_reset_email", side_effect=lambda *a, **kw: captured_tokens.append(kw.get("reset_token") or a[1]) or True):
            client.post("/api/auth/forgot-password", json={"email": self.USER_EMAIL})

        raw_token = captured_tokens[0]

        # Use token once
        first_use = client.post("/api/auth/reset-password", json={
            "token": raw_token,
            "new_password": "PasswordRoundOne123!"
        })
        assert first_use.status_code == 200

        # Attempt to use the same token again
        second_use = client.post("/api/auth/reset-password", json={
            "token": raw_token,
            "new_password": "PasswordRoundTwo456!"
        })
        assert second_use.status_code == 400
        assert "already been used" in second_use.json()["detail"]
        db.close()

    def test_12_revoked_token_is_rejected(self):
        """Case 12: Manually revoked tokens are rejected."""
        self._ensure_user()
        captured_tokens = []
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == self.USER_EMAIL).first()
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
        db.commit()

        with patch.object(email_service, "send_password_reset_email", side_effect=lambda *a, **kw: captured_tokens.append(kw.get("reset_token") or a[1]) or True):
            client.post("/api/auth/forgot-password", json={"email": self.USER_EMAIL})

        raw_token = captured_tokens[0]

        # Revoke token
        token_record = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).first()
        token_record.is_revoked = True
        db.commit()
        db.close()

        res = client.post("/api/auth/reset-password", json={
            "token": raw_token,
            "new_password": "PasswordShouldFail123!"
        })
        assert res.status_code == 400
        assert "revoked" in res.json()["detail"]

    def test_13_invalid_short_password_is_rejected(self):
        """Case 13: Password policy enforces minimum length."""
        self._ensure_user()
        captured_tokens = []
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == self.USER_EMAIL).first()
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
        db.commit()

        with patch.object(email_service, "send_password_reset_email", side_effect=lambda *a, **kw: captured_tokens.append(kw.get("reset_token") or a[1]) or True):
            client.post("/api/auth/forgot-password", json={"email": self.USER_EMAIL})

        raw_token = captured_tokens[0]

        # Password with 4 characters (< 6)
        res = client.post("/api/auth/reset-password", json={
            "token": raw_token,
            "new_password": "1234"
        })
        assert res.status_code in (400, 422)
        db.close()

    def test_14_new_reset_request_invalidates_previous_token(self):
        """Case 14: A subsequent reset request revokes earlier unused tokens."""
        self._ensure_user()
        tokens = []
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == self.USER_EMAIL).first()
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
        db.commit()

        # Request 1
        with patch.object(email_service, "send_password_reset_email", side_effect=lambda *a, **kw: tokens.append(kw.get("reset_token") or a[1]) or True):
            client.post("/api/auth/forgot-password", json={"email": self.USER_EMAIL})

        token_1 = tokens[0]

        # Move creation time of token_1 back 65 seconds to satisfy rate cooldown
        tok1_rec = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).first()
        tok1_rec.created_at = datetime.datetime.utcnow() - datetime.timedelta(seconds=65)
        db.commit()

        # Request 2
        with patch.object(email_service, "send_password_reset_email", side_effect=lambda *a, **kw: tokens.append(kw.get("reset_token") or a[1]) or True):
            client.post("/api/auth/forgot-password", json={"email": self.USER_EMAIL})

        token_2 = tokens[1]
        assert token_1 != token_2

        # Token 1 should now be rejected as superseded / revoked
        res_old = client.post("/api/auth/reset-password", json={
            "token": token_1,
            "new_password": "PasswordFromOldToken123!"
        })
        assert res_old.status_code == 400
        assert "revoked" in res_old.json()["detail"]

        # Token 2 should succeed
        res_new = client.post("/api/auth/reset-password", json={
            "token": token_2,
            "new_password": "PasswordFromNewToken456!"
        })
        assert res_new.status_code == 200
        db.close()

    def test_15_email_delivery_failure_handled_safely(self):
        """Case 15: If SMTP fails or raises an error, request does not crash or reveal failure to client."""
        self._ensure_user()
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == self.USER_EMAIL).first()
        # Ensure cooldown doesn't block
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
        db.commit()
        db.close()

        with patch.object(email_service, "send_password_reset_email", side_effect=Exception("Simulated SMTP Network Failure")):
            res = client.post("/api/auth/forgot-password", json={"email": self.USER_EMAIL})

        assert res.status_code == 200
        assert res.json()["status"] == "success"
        assert "If that email address is registered" in res.json()["message"]

    def test_16_refresh_token_revocation_on_password_reset(self):
        """Case 16: Existing refresh token is rejected after user resets password."""
        self._ensure_user()
        db = TestingSessionLocal()
        user = db.query(User).filter(User.email == self.USER_EMAIL).first()
        user.hashed_password = hash_password("PreResetPassword123!")
        user.password_changed_at = None
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
        db.commit()
        db.close()

        # Login to obtain fresh refresh token
        login_res = client.post("/api/login", json={
            "email": self.USER_EMAIL,
            "password": "PreResetPassword123!"
        })
        assert login_res.status_code == 200
        old_refresh_token = login_res.json()["refresh_token"]

        # User resets password
        captured_tokens = []
        with patch.object(email_service, "send_password_reset_email", side_effect=lambda *a, **kw: captured_tokens.append(kw.get("reset_token") or a[1]) or True):
            client.post("/api/auth/forgot-password", json={"email": self.USER_EMAIL})

        # Complete password reset
        reset_res = client.post("/api/auth/reset-password", json={
            "token": captured_tokens[0],
            "new_password": "PostResetPassword456!"
        })
        assert reset_res.status_code == 200

        # Attempt to use the old refresh token issued before the password reset
        refresh_res = client.post("/api/refresh", json={"refresh_token": old_refresh_token})
        assert refresh_res.status_code == 401
        assert "Session expired" in refresh_res.json()["detail"]

    def test_17_safe_local_mode_without_smtp(self):
        """Case 17: In local dev when SMTP_HOST is not set, email_service operates safely."""
        with patch.dict(os.environ, {"SMTP_HOST": ""}):
            result = email_service.send_password_reset_email("test@example.com", "dummy_token")
            assert result is True
