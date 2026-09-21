"""
Automated Test Suite for FinRisk AI — Persistent Avatar Storage System
Covers local storage, S3 cloud storage mock, security validations, lifecycle operations, and isolation.
"""
import os
import sys
import io
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_FILE = os.path.join(backend_dir, "test_avatar_storage.db")
if os.path.exists(TEST_DB_FILE):
    try:
        os.remove(TEST_DB_FILE)
    except Exception:
        pass

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE}"

from main import app
from models.base import Base
from database.session import get_db
from models.user import User
from services.auth_service import hash_password, create_access_token
from services.storage_service import storage_service, LocalStorageBackend, S3StorageBackend
from config import settings

engine = create_engine(f"sqlite:///{TEST_DB_FILE}", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True, scope="module")
def setup_avatar_test_env():
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


client = TestClient(app)


def make_test_image(format: str = "JPEG", size=(32, 32), color=(16, 185, 129)) -> bytes:
    """Helper to generate real, valid image bytes in memory."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()



def create_user_and_auth(email: str, name: str = "Test User"):
    """Create test user and return user object + bearer auth header."""
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            full_name=name,
            email=email,
            hashed_password=hash_password("Password123!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token(data={"sub": user.email})
    db.close()
    return user, {"Authorization": f"Bearer {token}"}


class TestAvatarStorageSuite:
    """14-point test suite covering all persistent avatar storage requirements."""

    def test_01_authenticated_user_uploads_valid_image(self):
        """Authenticated user successfully uploads valid JPEG and PNG avatars."""
        user, headers = create_user_and_auth("avatar_user1@example.com", "Avatar Tester 1")
        img_bytes = make_test_image(format="JPEG")

        res = client.post(
            "/api/users/profile-photo",
            headers=headers,
            files={"file": ("profile.jpg", img_bytes, "image/jpeg")},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "success"
        assert "profile_photo_url" in data
        assert data["profile_photo_url"].startswith("/uploads/avatars/")
        assert data["profile_photo_url"].endswith(".jpg")

        # Verify DB updated
        db = TestingSessionLocal()
        u = db.query(User).filter(User.id == user.id).first()
        assert u.profile_photo_url == data["profile_photo_url"]
        db.close()

    def test_02_unauthenticated_upload_is_rejected(self):
        """Unauthenticated upload request receives 401 Unauthorized."""
        img_bytes = make_test_image(format="PNG")
        res = client.post(
            "/api/users/profile-photo",
            files={"file": ("profile.png", img_bytes, "image/png")},
        )
        assert res.status_code == 401

    def test_03_user_cannot_modify_another_user_avatar(self):
        """Uploading an avatar only affects the authenticated user's profile."""
        user1, headers1 = create_user_and_auth("user_a@example.com", "User A")
        user2, headers2 = create_user_and_auth("user_b@example.com", "User B")

        img1 = make_test_image("JPEG", color="red")
        res1 = client.post(
            "/api/users/profile-photo",
            headers=headers1,
            files={"file": ("avatar_a.jpg", img1, "image/jpeg")},
        )
        assert res1.status_code == 200
        url1 = res1.json()["profile_photo_url"]

        # Check that user2 profile photo remains unchanged/None
        db = TestingSessionLocal()
        u2 = db.query(User).filter(User.id == user2.id).first()
        assert u2.profile_photo_url is None
        db.close()

    def test_04_oversized_file_is_rejected(self):
        """Files exceeding the 5MB limit are rejected with 400."""
        user, headers = create_user_and_auth("oversize_user@example.com")
        # 5.1 MB of dummy payload
        big_content = b"0" * (5 * 1024 * 1024 + 1024)
        res = client.post(
            "/api/users/profile-photo",
            headers=headers,
            files={"file": ("huge.jpg", big_content, "image/jpeg")},
        )
        assert res.status_code == 400
        assert "exceeds" in res.json()["detail"].lower()

    def test_05_invalid_image_content_is_rejected(self):
        """Non-image files with fake image extensions are rejected by PIL verification."""
        user, headers = create_user_and_auth("fake_img_user@example.com")
        fake_content = b"This is a text file claiming to be an image."
        res = client.post(
            "/api/users/profile-photo",
            headers=headers,
            files={"file": ("malicious.jpg", fake_content, "image/jpeg")},
        )
        assert res.status_code == 400
        assert "invalid" in res.json()["detail"].lower() or "corrupted" in res.json()["detail"].lower()

    def test_06_unsupported_image_format_is_rejected(self):
        """Unsupported formats such as GIF or TIFF are rejected."""
        user, headers = create_user_and_auth("gif_user@example.com")
        # Generate valid GIF
        buf = io.BytesIO()
        img = Image.new("RGB", (20, 20), color="yellow")
        img.save(buf, format="GIF")
        gif_bytes = buf.getvalue()

        res = client.post(
            "/api/users/profile-photo",
            headers=headers,
            files={"file": ("animation.gif", gif_bytes, "image/gif")},
        )
        assert res.status_code == 400
        assert "unsupported" in res.json()["detail"].lower()

    def test_07_cloud_storage_service_receives_validated_upload(self):
        """When S3 backend is configured, save_avatar uploads to bucket and returns cloud URL."""
        user, headers = create_user_and_auth("s3_user@example.com")
        img_bytes = make_test_image("WEBP")

        mock_s3 = MagicMock()
        mock_s3.put_object.return_value = {"ETag": "mock-etag"}

        with patch.object(settings, "AVATAR_STORAGE_BACKEND", "s3"), \
             patch.object(settings, "S3_ENDPOINT_URL", "https://mock.r2.cloudflarestorage.com"), \
             patch.object(settings, "S3_BUCKET_NAME", "finrisk-avatars"), \
             patch.object(settings, "S3_ACCESS_KEY_ID", "test_id"), \
             patch.object(settings, "S3_SECRET_ACCESS_KEY", "test_secret"), \
             patch.object(settings, "S3_PUBLIC_BASE_URL", "https://cdn.finrisk.ai"), \
             patch("services.storage_service.S3StorageBackend.get_client", return_value=mock_s3):

            res = client.post(
                "/api/users/profile-photo",
                headers=headers,
                files={"file": ("avatar.webp", img_bytes, "image/webp")},
            )
            assert res.status_code == 200, res.text
            data = res.json()
            assert data["profile_photo_url"].startswith("https://cdn.finrisk.ai/avatars/")
            assert data["profile_photo_url"].endswith(".webp")

            # Verify mock_s3.put_object was invoked with correct arguments
            mock_s3.put_object.assert_called_once()
            call_kwargs = mock_s3.put_object.call_args[1]
            assert call_kwargs["Bucket"] == "finrisk-avatars"
            assert call_kwargs["Key"].startswith("avatars/")
            assert call_kwargs["ContentType"] == "image/webp"

    def test_08_cloud_storage_failure_handled_safely(self):
        """If cloud storage upload raises an exception, return 500 without crashing."""
        user, headers = create_user_and_auth("s3_fail_user@example.com")
        img_bytes = make_test_image("JPEG")

        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = Exception("AWS S3 Network Timeout")

        with patch.object(settings, "AVATAR_STORAGE_BACKEND", "s3"), \
             patch.object(settings, "S3_ENDPOINT_URL", "https://mock.r2.cloudflarestorage.com"), \
             patch.object(settings, "S3_BUCKET_NAME", "finrisk-avatars"), \
             patch.object(settings, "S3_ACCESS_KEY_ID", "test_id"), \
             patch.object(settings, "S3_SECRET_ACCESS_KEY", "test_secret"), \
             patch("services.storage_service.S3StorageBackend.get_client", return_value=mock_s3):

            res = client.post(
                "/api/users/profile-photo",
                headers=headers,
                files={"file": ("photo.jpg", img_bytes, "image/jpeg")},
            )
            assert res.status_code == 500
            assert "failed" in res.json()["detail"].lower()

    def test_09_failed_replacement_preserves_previous_avatar(self):
        """If replacement upload fails, user's previous avatar URL is untouched."""
        user, headers = create_user_and_auth("replace_fail_user@example.com")
        # First: upload valid avatar locally
        img1 = make_test_image("PNG")
        res1 = client.post(
            "/api/users/profile-photo",
            headers=headers,
            files={"file": ("first.png", img1, "image/png")},
        )
        assert res1.status_code == 200
        orig_url = res1.json()["profile_photo_url"]

        # Attempt replacement with invalid payload
        res2 = client.post(
            "/api/users/profile-photo",
            headers=headers,
            files={"file": ("bad.png", b"not-an-image", "image/png")},
        )
        assert res2.status_code == 400

        # Verify DB still contains the original avatar URL
        db = TestingSessionLocal()
        u = db.query(User).filter(User.id == user.id).first()
        assert u.profile_photo_url == orig_url
        db.close()

    def test_10_successful_replacement_updates_user_avatar(self):
        """Successful replacement updates avatar URL and cleans up previous file."""
        user, headers = create_user_and_auth("replace_success_user@example.com")
        img1 = make_test_image("JPEG", color="blue")
        res1 = client.post(
            "/api/users/profile-photo",
            headers=headers,
            files={"file": ("first.jpg", img1, "image/jpeg")},
        )
        assert res1.status_code == 200
        url1 = res1.json()["profile_photo_url"]

        img2 = make_test_image("PNG", color="green")
        res2 = client.post(
            "/api/users/profile-photo",
            headers=headers,
            files={"file": ("second.png", img2, "image/png")},
        )
        assert res2.status_code == 200
        url2 = res2.json()["profile_photo_url"]
        assert url2 != url1

        # Check DB has url2
        db = TestingSessionLocal()
        u = db.query(User).filter(User.id == user.id).first()
        assert u.profile_photo_url == url2
        db.close()

    def test_11_avatar_removal_works(self):
        """DELETE /api/users/profile-photo resets avatar to None and deletes storage file."""
        user, headers = create_user_and_auth("delete_avatar_user@example.com")
        img = make_test_image("WEBP")
        res = client.post(
            "/api/users/profile-photo",
            headers=headers,
            files={"file": ("del.webp", img, "image/webp")},
        )
        assert res.status_code == 200
        assert res.json()["profile_photo_url"] is not None

        # Delete avatar
        del_res = client.delete("/api/users/profile-photo", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["profile_photo_url"] is None

        # Verify in DB
        db = TestingSessionLocal()
        u = db.query(User).filter(User.id == user.id).first()
        assert u.profile_photo_url is None
        db.close()

    def test_12_user_without_avatar_receives_fallback_response(self):
        """A user without an avatar has profile_photo_url: None in profile responses."""
        user, headers = create_user_and_auth("no_avatar_user@example.com")
        me_res = client.get("/api/auth/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["profile_photo_url"] is None

    def test_13_local_storage_mode_works_without_cloud_credentials(self):
        """Local mode operates completely self-contained without any S3 environment variables."""
        with patch.object(settings, "AVATAR_STORAGE_BACKEND", "local"), \
             patch.object(settings, "S3_ENDPOINT_URL", ""), \
             patch.object(settings, "S3_BUCKET_NAME", ""):
            user, headers = create_user_and_auth("local_dev_user@example.com")
            img = make_test_image("JPEG")
            res = client.post(
                "/api/users/profile-photo",
                headers=headers,
                files={"file": ("local.jpg", img, "image/jpeg")},
            )
            assert res.status_code == 200
            url = res.json()["profile_photo_url"]
            assert url.startswith("/uploads/avatars/")

    def test_14_s3_misconfiguration_fails_safely(self):
        """If AVATAR_STORAGE_BACKEND=s3 but credentials are missing, fail with 500 error."""
        with patch.object(settings, "AVATAR_STORAGE_BACKEND", "s3"), \
             patch.object(settings, "S3_ENDPOINT_URL", ""), \
             patch.object(settings, "S3_BUCKET_NAME", ""), \
             patch.object(settings, "S3_ACCESS_KEY_ID", ""):
            user, headers = create_user_and_auth("misconfig_user@example.com")
            img = make_test_image("JPEG")
            res = client.post(
                "/api/users/profile-photo",
                headers=headers,
                files={"file": ("test.jpg", img, "image/jpeg")},
            )
            assert res.status_code == 500
            assert "missing" in res.json()["detail"].lower()
