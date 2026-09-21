import os
import logging
from abc import ABC, abstractmethod
from urllib.parse import urlparse
from config import settings

logger = logging.getLogger("storage_service")

# Resolve upload base directory
upload_base = "/tmp" if os.getenv("VERCEL") else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOCAL_UPLOADS_DIR = os.path.abspath(os.path.join(upload_base, "uploads"))
LOCAL_AVATARS_DIR = os.path.join(LOCAL_UPLOADS_DIR, "avatars")


class BaseStorageBackend(ABC):
    @abstractmethod
    def save_avatar(self, content: bytes, filename: str, content_type: str) -> str:
        """Save avatar bytes and return the public URL or static path."""
        pass

    @abstractmethod
    def delete_avatar(self, avatar_url_or_key: str) -> bool:
        """Delete avatar from storage. Returns True if deleted or already absent."""
        pass


class LocalStorageBackend(BaseStorageBackend):
    def __init__(self, base_dir: str = LOCAL_AVATARS_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save_avatar(self, content: bytes, filename: str, content_type: str) -> str:
        # Sanitize filename (only basename)
        safe_filename = os.path.basename(filename)
        dest_path = os.path.join(self.base_dir, safe_filename)

        # Write to disk
        with open(dest_path, "wb") as f:
            f.write(content)

        logger.info(f"Avatar saved locally to {safe_filename}")
        return f"/uploads/avatars/{safe_filename}"

    def delete_avatar(self, avatar_url_or_key: str) -> bool:
        if not avatar_url_or_key:
            return True

        # Extract filename from path e.g. /uploads/avatars/xyz.webp or /uploads/xyz.jpg
        parsed = urlparse(avatar_url_or_key).path
        filename = os.path.basename(parsed)
        if not filename:
            return False

        # Try both avatars subdir and root uploads dir for backward compatibility
        candidate_paths = [
            os.path.join(self.base_dir, filename),
            os.path.join(LOCAL_UPLOADS_DIR, filename),
        ]

        deleted = False
        for path in candidate_paths:
            normalized = os.path.abspath(path)
            # Prevent path traversal outside LOCAL_UPLOADS_DIR
            if normalized.startswith(LOCAL_UPLOADS_DIR) and os.path.exists(normalized):
                try:
                    os.remove(normalized)
                    logger.info(f"Local avatar deleted: {filename}")
                    deleted = True
                except Exception as e:
                    logger.warning(f"Failed to delete local avatar file: {e}")

        return deleted


class S3StorageBackend(BaseStorageBackend):
    def __init__(
        self,
        endpoint_url: str = None,
        bucket_name: str = None,
        access_key_id: str = None,
        secret_access_key: str = None,
        region: str = None,
        public_base_url: str = None,
    ):
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.access_key_id = access_key_id or settings.S3_ACCESS_KEY_ID
        self.secret_access_key = secret_access_key or settings.S3_SECRET_ACCESS_KEY
        self.region = region or settings.S3_REGION or "auto"
        self.public_base_url = (public_base_url or settings.S3_PUBLIC_BASE_URL).rstrip("/")

        self._validate_config()
        self._client = None

    def _validate_config(self):
        missing = []
        if not self.endpoint_url:
            missing.append("S3_ENDPOINT_URL")
        if not self.bucket_name:
            missing.append("S3_BUCKET_NAME")
        if not self.access_key_id:
            missing.append("S3_ACCESS_KEY_ID")
        if not self.secret_access_key:
            missing.append("S3_SECRET_ACCESS_KEY")

        if missing:
            err_msg = (
                f"Cloud avatar storage is enabled (AVATAR_STORAGE_BACKEND=s3), "
                f"but required configuration is missing: {', '.join(missing)}. "
                "Please configure these environment variables."
            )
            logger.error(err_msg)
            raise ValueError(err_msg)

    def get_client(self):
        if self._client is None:
            import boto3
            from botocore.config import Config

            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region,
                config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
            )
        return self._client

    def save_avatar(self, content: bytes, filename: str, content_type: str) -> str:
        safe_filename = os.path.basename(filename)
        key = f"avatars/{safe_filename}"
        client = self.get_client()

        try:
            client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
            logger.info(f"Avatar uploaded to S3/R2 bucket '{self.bucket_name}' key '{key}'")
        except Exception as e:
            logger.error(f"S3/R2 PutObject failed for key '{key}': {e}")
            raise RuntimeError("Cloud storage upload failed.") from e

        if self.public_base_url:
            return f"{self.public_base_url}/{key}"
        return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{key}"

    def delete_avatar(self, avatar_url_or_key: str) -> bool:
        if not avatar_url_or_key:
            return True

        key = self._extract_key(avatar_url_or_key)
        if not key:
            return False

        client = self.get_client()
        try:
            client.delete_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            logger.info(f"Avatar deleted from S3/R2 key: '{key}'")
            return True
        except Exception as e:
            logger.warning(f"S3/R2 DeleteObject failed for key '{key}': {e}")
            return False

    def _extract_key(self, url_or_key: str) -> str:
        if not url_or_key:
            return ""
        if url_or_key.startswith("avatars/"):
            return url_or_key

        parsed = urlparse(url_or_key)
        path = parsed.path.lstrip("/")

        # Check if bucket name is in the path
        if path.startswith(f"{self.bucket_name}/"):
            path = path[len(self.bucket_name) + 1:]

        if path.startswith("avatars/"):
            return path

        return f"avatars/{os.path.basename(path)}"


class AvatarStorageService:
    def __init__(self):
        self._local_backend = LocalStorageBackend()

    def get_backend(self) -> BaseStorageBackend:
        backend_type = getattr(settings, "AVATAR_STORAGE_BACKEND", "local").lower().strip()
        if backend_type == "s3":
            return S3StorageBackend()
        return self._local_backend

    def save_avatar(self, content: bytes, filename: str, content_type: str) -> str:
        backend = self.get_backend()
        return backend.save_avatar(content, filename, content_type)

    def delete_avatar(self, avatar_url_or_key: str) -> bool:
        if not avatar_url_or_key:
            return True

        # If it's a local static upload URL or path
        if avatar_url_or_key.startswith("/uploads/") or "/uploads/" in avatar_url_or_key:
            return self._local_backend.delete_avatar(avatar_url_or_key)

        # Otherwise dispatch to configured backend
        backend = self.get_backend()
        return backend.delete_avatar(avatar_url_or_key)


# Global storage service instance
storage_service = AvatarStorageService()
