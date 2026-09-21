"""
CORS Security and Hardening Test Suite — Task 23

Tests all CORS resolution paths and HTTP behavior against requirements:
1. Allowed configured origins (including Vercel URL and custom domain)
2. Rejected unconfigured origins
3. Missing/empty production configuration (never falls back to wildcard)
4. Local development behavior (defaults to localhost origins with credentials)
5. Credentials are never combined with wildcard origins
6. Malformed input sanitization (whitespace, trailing slashes, missing scheme)
"""
import os
import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.testclient import TestClient

from config import resolve_cors_origins, DEFAULT_DEV_ORIGINS


def create_cors_app(raw_origins: str | None, is_production: bool) -> FastAPI:
    """Helper to instantiate a FastAPI test app with resolved CORS middleware."""
    app = FastAPI()
    allowed_origins, allow_credentials = resolve_cors_origins(
        raw_origins=raw_origins,
        is_production=is_production,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/login")
    def login():
        return {"authenticated": True}

    return app


# ─────────────────────────────────────────────────────────────────────────────
# 1. Unit Tests: Origin Resolution Logic
# ─────────────────────────────────────────────────────────────────────────────

class TestResolveCorsOriginsUnit:
    """Validates the security rules in resolve_cors_origins."""

    def test_production_missing_origins_returns_empty_and_no_credentials(self):
        """In production, missing ALLOWED_ORIGINS must NOT fall back to wildcard."""
        origins, allow_creds = resolve_cors_origins(raw_origins=None, is_production=True)
        assert origins == []
        assert allow_creds is False

    def test_production_empty_string_returns_empty_and_no_credentials(self):
        """In production, empty ALLOWED_ORIGINS must NOT fall back to wildcard."""
        origins, allow_creds = resolve_cors_origins(raw_origins="", is_production=True)
        assert origins == []
        assert allow_creds is False

        origins_whitespace, allow_creds_ws = resolve_cors_origins(raw_origins="   ", is_production=True)
        assert origins_whitespace == []
        assert allow_creds_ws is False

    def test_production_malformed_only_commas_returns_empty(self):
        """Commas and spaces with no actual origin resolve to empty list in production."""
        origins, allow_creds = resolve_cors_origins(raw_origins=" , , ,, ", is_production=True)
        assert origins == []
        assert allow_creds is False

    def test_development_missing_origins_uses_localhost_defaults(self):
        """In development, missing ALLOWED_ORIGINS uses safe localhost defaults."""
        origins, allow_creds = resolve_cors_origins(raw_origins=None, is_production=False)
        assert origins == DEFAULT_DEV_ORIGINS
        assert "http://localhost:5173" in origins
        assert "http://127.0.0.1:5173" in origins
        assert allow_creds is True

    def test_development_empty_string_uses_localhost_defaults(self):
        """In development, empty string uses safe localhost defaults."""
        origins, allow_creds = resolve_cors_origins(raw_origins="   ", is_production=False)
        assert origins == DEFAULT_DEV_ORIGINS
        assert allow_creds is True

    def test_configured_single_origin_with_credentials(self):
        """A valid configured origin allows credentials."""
        origins, allow_creds = resolve_cors_origins(
            raw_origins="https://finrisk-ai.vercel.app",
            is_production=True,
        )
        assert origins == ["https://finrisk-ai.vercel.app"]
        assert allow_creds is True

    def test_configured_multiple_origins_including_custom_domain(self):
        """Multiple comma-separated origins (e.g. Vercel + custom domain) are parsed correctly."""
        raw = "https://finrisk-ai.vercel.app, https://app.finrisk.ai, https://finrisk.ai"
        origins, allow_creds = resolve_cors_origins(raw_origins=raw, is_production=True)
        assert origins == [
            "https://finrisk-ai.vercel.app",
            "https://app.finrisk.ai",
            "https://finrisk.ai",
        ]
        assert allow_creds is True

    def test_sanitizes_trailing_slashes_and_whitespace(self):
        """Trailing slashes and surrounding whitespace are stripped from origins."""
        raw = "  https://finrisk-ai.vercel.app/  ,   https://app.finrisk.ai/  "
        origins, allow_creds = resolve_cors_origins(raw_origins=raw, is_production=True)
        assert origins == ["https://finrisk-ai.vercel.app", "https://app.finrisk.ai"]

    def test_normalizes_missing_scheme_to_https(self):
        """Origins specified without scheme default safely to https://."""
        raw = "finrisk-ai.vercel.app, custom.domain.com"
        origins, allow_creds = resolve_cors_origins(raw_origins=raw, is_production=True)
        assert origins == ["https://finrisk-ai.vercel.app", "https://custom.domain.com"]

    def test_deduplicates_origins_preserving_order(self):
        """Duplicate entries are filtered out while preserving first seen order."""
        raw = "https://app.vercel.app, https://app.vercel.app/, https://custom.com, https://app.vercel.app"
        origins, allow_creds = resolve_cors_origins(raw_origins=raw, is_production=True)
        assert origins == ["https://app.vercel.app", "https://custom.com"]

    def test_wildcard_origin_never_allows_credentials(self):
        """Explicit wildcard origin must ALWAYS force allow_credentials=False."""
        origins, allow_creds = resolve_cors_origins(raw_origins="*", is_production=True)
        assert origins == ["*"]
        assert allow_creds is False

    def test_wildcard_mixed_with_other_origins_forces_wildcard_without_credentials(self):
        """If wildcard is mixed with specific origins, credentials must remain disabled."""
        origins, allow_creds = resolve_cors_origins(raw_origins="https://app.vercel.app, *", is_production=True)
        assert origins == ["*"]
        assert allow_creds is False


# ─────────────────────────────────────────────────────────────────────────────
# 2. Integration Tests: HTTP Preflight & Request Behavior
# ─────────────────────────────────────────────────────────────────────────────

class TestCorsHttpBehavior:
    """Verifies actual HTTP response headers for allowed and unconfigured origins."""

    def test_allowed_configured_origin_receives_cors_headers(self):
        """Configured Vercel origin receives Access-Control-Allow-Origin and Credentials headers."""
        app = create_cors_app(
            raw_origins="https://finrisk-ai.vercel.app, https://app.finrisk.ai",
            is_production=True,
        )
        client = TestClient(app)

        # GET request from configured origin
        res = client.get("/api/health", headers={"Origin": "https://finrisk-ai.vercel.app"})
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == "https://finrisk-ai.vercel.app"
        assert res.headers.get("access-control-allow-credentials") == "true"

        # OPTIONS preflight request
        preflight = client.options(
            "/api/login",
            headers={
                "Origin": "https://finrisk-ai.vercel.app",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers.get("access-control-allow-origin") == "https://finrisk-ai.vercel.app"
        assert preflight.headers.get("access-control-allow-credentials") == "true"
        assert "POST" in preflight.headers.get("access-control-allow-methods", "")

    def test_custom_domain_origin_receives_cors_headers(self):
        """Configured custom domain origin is allowed."""
        app = create_cors_app(
            raw_origins="https://finrisk-ai.vercel.app, https://app.finrisk.ai",
            is_production=True,
        )
        client = TestClient(app)

        res = client.get("/api/health", headers={"Origin": "https://app.finrisk.ai"})
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == "https://app.finrisk.ai"
        assert res.headers.get("access-control-allow-credentials") == "true"

    def test_unconfigured_origin_is_rejected(self):
        """Unconfigured origin receives NO Access-Control-Allow-Origin header."""
        app = create_cors_app(
            raw_origins="https://finrisk-ai.vercel.app",
            is_production=True,
        )
        client = TestClient(app)

        # GET request from unknown origin
        res = client.get("/api/health", headers={"Origin": "https://malicious-site.com"})
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") is None

        # Preflight from unknown origin
        preflight = client.options(
            "/api/login",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        # CORSMiddleware does not return allow-origin header for rejected origins
        assert preflight.headers.get("access-control-allow-origin") is None

    def test_missing_production_config_rejects_all_origins(self):
        """In production without ALLOWED_ORIGINS, all cross-origin requests are denied."""
        app = create_cors_app(raw_origins="", is_production=True)
        client = TestClient(app)

        # Attempt from any origin
        res = client.get("/api/health", headers={"Origin": "https://finrisk-ai.vercel.app"})
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") is None

        # Preflight attempt
        preflight = client.options(
            "/api/health",
            headers={
                "Origin": "https://finrisk-ai.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert preflight.headers.get("access-control-allow-origin") is None

    def test_local_development_allows_localhost_with_credentials(self):
        """In local development without ALLOWED_ORIGINS, localhost origins work with credentials."""
        app = create_cors_app(raw_origins="", is_production=False)
        client = TestClient(app)

        # Port 5173 (Vite dev)
        res_5173 = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        assert res_5173.status_code == 200
        assert res_5173.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert res_5173.headers.get("access-control-allow-credentials") == "true"

        # 127.0.0.1:5173
        res_ip = client.get("/api/health", headers={"Origin": "http://127.0.0.1:5173"})
        assert res_ip.status_code == 200
        assert res_ip.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"
        assert res_ip.headers.get("access-control-allow-credentials") == "true"

        # External origin in dev still rejected if not configured
        res_ext = client.get("/api/health", headers={"Origin": "https://external-site.com"})
        assert res_ext.headers.get("access-control-allow-origin") is None

    def test_wildcard_cors_does_not_return_credentials_true(self):
        """When wildcard is configured, Access-Control-Allow-Credentials must not be 'true'."""
        app = create_cors_app(raw_origins="*", is_production=False)
        client = TestClient(app)

        res = client.get("/api/health", headers={"Origin": "https://any-origin.com"})
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == "*"
        assert res.headers.get("access-control-allow-credentials") is None


# ─────────────────────────────────────────────────────────────────────────────
# 3. Integration Tests: Live Backend main:app Verification
# ─────────────────────────────────────────────────────────────────────────────

def test_live_main_app_cors_middleware():
    """Verifies that main.app is wired with the hardened CORS middleware."""
    from main import app
    client = TestClient(app)

    # In current local test environment, default dev origins are active
    res = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert res.headers.get("access-control-allow-credentials") == "true"

    # Unauthorized origin
    res_bad = client.get("/health", headers={"Origin": "https://unauthorized-domain.com"})
    assert res_bad.headers.get("access-control-allow-origin") is None
