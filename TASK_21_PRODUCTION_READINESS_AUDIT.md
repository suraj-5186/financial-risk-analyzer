# FinRisk AI — Production Readiness Audit
**Report Type:** Comprehensive Read-Only Audit  
**Task Reference:** TASK 21  
**Date:** September 21, 2026  
**Auditor:** Antigravity AI (Senior Software Architect + QA Auditor)  
**Status at Audit Time:** Tasks 1–20 implemented, pre-deployment

> **Important**: No secrets, credentials, API keys, passwords, or raw tokens are exposed in this report. This is a read-only analysis.

---

## 1. Executive Summary

FinRisk AI is a sophisticated, full-stack personal finance and risk analysis platform with a React 19 + TypeScript frontend hosted on Vercel and a FastAPI + SQLAlchemy backend hosted on Render, backed by PostgreSQL in production and SQLite locally.

**Overall Assessment: Conditionally Ready for Deployment**

The application is functionally mature — all 20 planned tasks have been implemented, test suites exist for every major feature, and deployment configuration is largely in place. However, **two critical blockers** must be resolved before the production deployment will succeed:

1. **`render.yaml` references the root `requirements.txt`**, which is significantly incomplete compared to `backend/requirements.txt`. Key production dependencies — `pandas`, `numpy`, `scikit-learn`, `joblib`, `boto3`, `pillow` — are missing from the root file. The Render build will fail silently or error at runtime.

2. **`ALLOWED_ORIGINS` in `render.yaml` is set to an empty string**, which causes the CORS middleware to fall back to wildcard (`"*"`) mode with `allow_credentials=False`. This means authenticated cross-origin requests from Vercel will fail (browsers block credentials with wildcard CORS origins).

Three additional high-priority items require action before first production launch:

- `cryptography` package (required by `bank_security.py`) is not explicitly listed in either `requirements.txt`.
- `FRONTEND_URL` and `SMTP_*` variables must be configured on Render for password reset emails to work.
- Avatar uploads in production will silently fall back to local filesystem (ephemeral on Render) unless `AVATAR_STORAGE_BACKEND=s3` and S3 credentials are configured.

---

## 2. Repository Inventory

### 2.1 Directory Structure

```
financial-risk-analyzer/
├── backend/               # FastAPI application (Python 3.11+)
│   ├── main.py            # Application entry point, router registration, CORS setup
│   ├── config.py          # Pydantic-settings based environment configuration
│   ├── requirements.txt   # Complete backend dependencies (21 packages)
│   ├── Dockerfile         # Container image for backend
│   ├── database/
│   │   ├── session.py     # SQLAlchemy engine + session factory
│   │   └── migrations.py  # Custom idempotent migration runner
│   ├── models/            # 18 SQLAlchemy ORM models
│   ├── routers/           # 18 FastAPI route modules (~3,163 lines total)
│   ├── schemas/           # 17 Pydantic v2 schema files
│   └── services/          # 16 business-logic services
├── frontend/              # React 19 + TypeScript + Vite + TailwindCSS
│   ├── src/
│   │   ├── App.tsx        # Client-side routing (19 pages)
│   │   ├── pages/         # 19 page components
│   │   ├── services/      # API client modules (api.ts and 4 feature clients)
│   │   └── context/       # AuthContext (JWT + refresh token management)
│   ├── vite.config.ts     # Dev proxy: /api → localhost:8000
│   └── vercel.json        # SPA rewrite rule
├── ml/                    # Scikit-learn risk prediction pipeline
│   ├── predict.py         # Inference function (loaded by backend routers)
│   ├── risk_model.pkl     # Trained serialized model
│   └── train.py           # Training script
├── render.yaml            # Render Blueprint (backend + PostgreSQL database)
├── vercel.json            # Root Vercel deployment config (build + rewrites)
├── requirements.txt       # ROOT requirements — INCOMPLETE (14 packages only)
├── docker-compose.yml     # Local development orchestration
└── .env.example           # Comprehensive environment variable template
```

### 2.2 Feature Inventory

| Task | Feature | Status |
|------|---------|--------|
| 1 | Render deployment scaffolding | ✅ Implemented |
| 2 | Deployment preparation (Vercel + Render) | ✅ Implemented |
| 3 | Initial audit & README | ✅ Implemented |
| 15 | Password reset (email token flow) | ✅ Fully implemented |
| 16 | Persistent cloud avatar storage (S3/R2) | ✅ Implemented (needs env vars) |
| 17 | Bank statement auto-categorization | ✅ Implemented |
| 18 | Recurring subscription detector | ✅ Implemented |
| 19 | Bank sync foundation (mock + Plaid scaffold) | ✅ Implemented |
| 20 | Cash flow forecasting & financial health insights | ✅ Implemented |

### 2.3 Codebase Scale

- **Backend routers**: 18 modules, ~3,163 lines
- **Backend services**: 16 modules, ~130KB total
- **Frontend pages**: 19 pages
- **Test files**: 8 test files, ~4,661 lines total
- **Database models**: 18 ORM models

---

## 3. Detailed Findings

### 3.1 Deployment Configuration

#### 3.1.1 `render.yaml` — Backend Web Service

| Setting | Value | Status |
|---------|-------|--------|
| `type` | `web` | ✅ Correct |
| `runtime` | `python` | ✅ Correct |
| `rootDir` | `.` (repo root) | ⚠️ Means build runs from root, not `backend/` |
| `buildCommand` | `pip install -r requirements.txt` | ❌ Installs root (incomplete) requirements |
| `startCommand` | `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT` | ✅ Correct |
| `healthCheckPath` | `/health` | ✅ Health endpoint exists in `main.py` |
| `plan` | `free` | ✅ Set |
| `SECRET_KEY` | `generateValue: true` | ✅ Auto-generated per deployment |
| `ALLOWED_ORIGINS` | `""` (empty string) | ❌ Critical — causes wildcard CORS fallback |
| `GEMINI_API_KEY` | `""` (empty string) | ⚠️ AI chat falls back to rule-based engine |

**Critical Issue**: `buildCommand: pip install -r requirements.txt` installs from the root-level `requirements.txt` (14 packages), **not** `backend/requirements.txt` (21 packages). The root file is missing:
- `pandas`, `numpy`, `scikit-learn`, `joblib` — required by `ml/predict.py` (called in transaction and profile routers)
- `boto3` — required by `storage_service.py` for S3/R2 avatar storage
- `pillow` — required by `user.py` for image validation on upload
- `cryptography` — required by `bank_security.py` for Fernet encryption of bank tokens

#### 3.1.2 Root `vercel.json` — Frontend Deployment

```json
{
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/dist",
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

| Setting | Value | Status |
|---------|-------|--------|
| `buildCommand` | `cd frontend && npm install && npm run build` | ✅ Correct |
| `outputDirectory` | `frontend/dist` | ✅ Correct (Vite default output) |
| SPA rewrite | `/(.*) → /index.html` | ✅ Enables React Router deep links on refresh |

#### 3.1.3 `frontend/vercel.json`

Contains only the rewrite rule (duplicate of root). Safe but redundant — Vercel will use whichever is discovered first.

---

### 3.2 CORS Configuration

**File**: `backend/main.py` (lines 57–71)

```python
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
if _raw_origins and _raw_origins.strip() != "*":
    ALLOWED_ORIGINS = [o.strip().rstrip("/") for o in _raw_origins.split(",") if o.strip()]
    ALLOW_CREDENTIALS = True
else:
    ALLOWED_ORIGINS = ["*"]
    ALLOW_CREDENTIALS = False
```

**Production Issue**: In `render.yaml`, `ALLOWED_ORIGINS` is currently set to `value: ""` (empty string). The condition `if _raw_origins` evaluates to `False` for an empty string, causing the production backend to fall back to `ALLOWED_ORIGINS = ["*"]` with `ALLOW_CREDENTIALS = False`.

**Impact**: The frontend stores tokens in `localStorage` and sends them via `Authorization: Bearer` headers (not cookies), so `allow_credentials` technically doesn't matter for the primary auth flow. However, the wildcard origin means **any website on the internet can make API calls to the production backend** — an unnecessary security exposure.

**Action Required**: Set `ALLOWED_ORIGINS` to the production Vercel URL after deployment (e.g., `https://finrisk-ai.vercel.app`).

---

### 3.3 Authentication & Security

**File**: `backend/services/auth_service.py`

| Feature | Implementation | Status |
|---------|---------------|--------|
| Password hashing | bcrypt (salt rounds via `bcrypt.gensalt()`) | ✅ Secure |
| JWT algorithm | HS256 | ✅ Standard |
| Access token expiry | 30 minutes (configurable) | ✅ Appropriate |
| Refresh token expiry | 7 days (configurable) | ✅ Appropriate |
| Refresh token rotation | Issues new refresh token on refresh | ✅ Good |
| Token invalidation on password reset | `token_version` counter incremented | ✅ Implemented |
| Password reset | Secure random token, hashed in DB, 30-min expiry, single use | ✅ Excellent |
| Email enumeration prevention | Generic response for forgot-password | ✅ Correct |
| Token storage | `localStorage` (not HttpOnly cookies) | ⚠️ XSS-susceptible; common SPA pattern |
| Admin authorization | Application-level `is_admin` check per route | ✅ Functional |

**Security Finding — `config.py` default SECRET_KEY**:  
`config.py` line 6 specifies a fallback: `os.getenv("SECRET_KEY", "supersecretkeyforfinancialriskanalyzer1234567890!")`. On Render, `generateValue: true` ensures a unique key is generated. This is safe in the Blueprint deployment path. **Risk**: If Render is configured manually without setting `SECRET_KEY`, the hardcoded default would be used — mitigated by the Blueprint.

**Security Finding — `cryptography` not in `requirements.txt`**:  
`bank_security.py` imports `from cryptography.fernet import Fernet` and `from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC`. The `cryptography` package is currently a transitive dependency (pulled in via `google-generativeai` through `requests`), but this is fragile and version-dependent. It must be declared explicitly.

---

### 3.4 Database Schema & Migrations

**Files**: `backend/database/session.py`, `backend/database/migrations.py`

| Feature | Implementation | Status |
|---------|---------------|--------|
| SQLite/PostgreSQL compatibility | `postgres://` → `postgresql://` rewrite in `session.py` | ✅ |
| SQLite thread safety | `check_same_thread=False` | ✅ |
| Migration strategy | Custom idempotent `run_migrations()` via `ALTER TABLE IF NOT EXISTS` | ⚠️ Functional but fragile |
| New table creation | In-migration DDL for `recurring_payments`, `bank_connections`, `bank_accounts` | ✅ |
| Rollback support | None (forward-only) | ⚠️ No Alembic; cannot roll back schema changes |
| Connection pooling | Default SQLAlchemy pool (no `pool_pre_ping`) | ⚠️ Render free tier may drop idle connections |

**Notable**: `Base.metadata.create_all(bind=engine)` on startup will create all tables that don't exist yet. The custom `run_migrations()` handles incremental ALTER TABLEs for columns added after initial deployment. This is functional but would benefit from Alembic for long-term maintainability.

**Recommendation**: Add `pool_pre_ping=True` to the SQLAlchemy engine creation to handle Render's PostgreSQL connection recycling gracefully.

---

### 3.5 Email / Password Reset

**File**: `backend/services/email_service.py`

| Feature | Status |
|---------|--------|
| Real SMTP dispatch | ✅ Implemented with TLS support |
| Safe dev-mode fallback | ✅ Logs reset request without sending email when SMTP_HOST unset |
| HTML email template | ✅ Branded, responsive |
| Plaintext fallback | ✅ Included |
| Token URL construction | ✅ Uses `FRONTEND_URL` setting |
| Credential logging prevention | ✅ Only logs exception type, not credentials |

**Production Requirement**: `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `FRONTEND_URL` must be set on Render. Without them, the system will silently accept password reset requests (returns success) but never send emails. **This is not a crash blocker but is a functional gap.**

---

### 3.6 Avatar Storage

**File**: `backend/services/storage_service.py`

| Feature | Status |
|---------|--------|
| Local storage backend | ✅ Implemented |
| S3/R2 storage backend | ✅ Implemented (boto3-backed) |
| Backend selection | Environment variable `AVATAR_STORAGE_BACKEND` (`local` or `s3`) |
| Render ephemeral disk risk | ❌ Default `local` backend will lose uploads on Render restarts |
| S3 credential validation | ✅ Raises `ValueError` at startup if S3 configured but credentials missing |

**Production Requirement**: Set `AVATAR_STORAGE_BACKEND=s3` and configure `S3_ENDPOINT_URL`, `S3_BUCKET_NAME`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_PUBLIC_BASE_URL` for persistent avatar storage. Alternatively, configure a Render persistent disk and continue using local storage.

**Note**: `AVATAR_MAX_SIZE_BYTES` is referenced in `user.py` via `getattr(settings, "AVATAR_MAX_SIZE_BYTES", 5 * 1024 * 1024)` but is not declared as a typed field in `config.py` (Settings class). It is documented in `.env.example` only. Should be added to the Settings class.

---

### 3.7 Bank Sync Foundation (Task 19)

**Files**: `backend/services/bank_sync_service.py`, `backend/services/bank_providers/`

| Feature | Status |
|---------|--------|
| Mock provider | ✅ Fully functional for local dev and demo |
| Plaid scaffold | ✅ Scaffold only — raises `ProviderNotConfiguredException` if credentials absent |
| Token encryption at rest | ✅ Fernet (AES-128-CBC) — key derived from SECRET_KEY via PBKDF2 |
| Deduplication (primary) | ✅ `external_id` index |
| Deduplication (fallback) | ✅ Date + amount + type + description tuple |
| Auto-categorization on import | ✅ Calls `categorization_engine.categorize()` |
| Recurring detection on import | ✅ Calls `scan_user_recurring_payments()` after import |
| Real bank integration | ❌ Not live — requires `PLAID_CLIENT_ID` + `PLAID_SECRET` |

**Production Note**: Bank sync is clearly labeled as mock-only in production until Plaid credentials are configured. The UI should inform users that live bank connections are not yet available.

---

### 3.8 ML Risk Prediction

**Files**: `ml/predict.py`, `ml/risk_model.pkl`, `ml/risk_model.json`

| Feature | Status |
|---------|--------|
| Trained model | ✅ `risk_model.pkl` exists and is committed |
| Inference function | ✅ `predict_financial_risk()` in `predict.py` |
| Used in routers | ✅ Called in `transaction.py` and `profile.py` |
| Dependencies | ❌ `scikit-learn`, `numpy`, `pandas`, `joblib` missing from root `requirements.txt` |
| `.pkl` in `.gitignore` | Not excluded — binary committed directly | ⚠️ Acceptable for this scale |

---

### 3.9 Frontend Deployment

**File**: `frontend/src/services/api.ts` (line 1)

```typescript
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");
```

- Empty `VITE_API_BASE_URL` → all requests go to same origin (Vite dev proxy handles `/api/*`)
- Set `VITE_API_BASE_URL=https://finrisk-ai-backend.onrender.com` in Vercel environment → production routing works

| Feature | Status |
|---------|--------|
| API base URL via env var | ✅ Correct pattern |
| Dev proxy | ✅ `vite.config.ts` proxies `/api` and `/uploads` to `localhost:8000` |
| React Router SPA refresh | ✅ `vercel.json` rewrites all paths to `/index.html` |
| Token auto-refresh | ✅ Implemented in `api.ts` request wrapper |
| Auth context | ✅ `AuthContext.tsx` — `localStorage`-based, survives page refresh |
| Build command | ✅ `tsc -b && vite build` |

---

### 3.10 Auto-Categorization Engine (Task 17)

**File**: `backend/services/categorization_service.py`

- Rule-based engine with merchant keyword matching (India and international merchants)
- 14 defined categories + "Needs Review" fallback
- Confidence scoring: 0.95 (high), 0.75 (medium), 0.50 (income keyword), 0.30 (fallback)
- No external API call — works offline and has zero latency dependency
- Status: ✅ Production-ready

---

### 3.11 Recurring Payment Detector (Task 18)

**File**: `backend/services/recurring_service.py`

- Frequency detection: monthly, weekly, biweekly, quarterly, annual
- Confidence-weighted scoring; persists to `recurring_payments` table
- Triggered on bank sync import and manual scan
- Status: ✅ Production-ready

---

### 3.12 Cash Flow Forecasting & Insights (Task 20)

**Files**: `backend/services/cash_flow_service.py`, `backend/services/cash_flow_forecast_service.py`, `backend/services/financial_insights_service.py`

- Historical cash flow with 6-month trend, category breakdown, period comparison
- Deterministic 30-day and month-end forecast with double-counting prevention
- Rule-based insights: spending surge, category concentration, recurring burden, budget overrun
- All endpoints authenticated, user-scoped
- Status: ✅ Production-ready

---

## 4. Test Suite Verification

> **Note**: Tests were not re-executed during this audit. Results below reflect the last verified run (from Task 20 session).

| Test File | Coverage Area | Last Known Result |
|-----------|-------------|-------------------|
| `test_flow.py` | Core auth + transactions | Passed |
| `test_phase2_flow.py` | Extended feature suite (136 tests) | 136/136 Passed |
| `test_password_reset.py` | Password reset e2e | Passed |
| `test_avatar_storage.py` | Storage service (local + S3 mock) | Passed |
| `test_auto_categorization.py` | Categorization engine | Passed |
| `test_recurring_payments.py` | Recurring detector | Passed |
| `test_bank_sync.py` | Bank sync service | Passed |
| `test_cash_flow_insights.py` | Cash flow + insights (10 tests) | 10/10 Passed |

**What is not tested:**
- End-to-end frontend behavior (no Playwright/Cypress tests)
- PostgreSQL-specific behavior (all tests use SQLite)
- SMTP email delivery in production
- Real S3/R2 upload flow
- Real Plaid/bank provider integration

---

## 5. Deployment Blockers

These must be resolved before the first production deployment will succeed.

### BLOCKER 1 — Render uses incomplete root `requirements.txt`

**Severity: Critical**  
**Impact**: Runtime `ImportError` on first request to ML prediction, avatar upload, or bank sync endpoints.

`render.yaml` sets `rootDir: .` and `buildCommand: pip install -r requirements.txt`. This installs only 14 packages from the root file. The backend actually needs 21 packages (from `backend/requirements.txt`).

**Missing from root `requirements.txt`**:
- `pandas>=2.0.0`
- `numpy>=1.24.0`
- `scikit-learn>=1.2.0`
- `joblib>=1.3.0`
- `boto3>=1.34.0`
- `pillow>=10.0.0`

**Fix Option A** (minimal change): Update `render.yaml` `buildCommand` to `pip install -r backend/requirements.txt`  
**Fix Option B** (canonical): Merge `backend/requirements.txt` into root `requirements.txt` and add `cryptography>=41.0.0`

---

### BLOCKER 2 — `ALLOWED_ORIGINS` not set for production

**Severity: Critical**  
**Impact**: Production CORS will allow all origins (`"*"`). While the primary auth flow (Bearer header) still technically works with wildcard CORS, this is a security exposure. More critically, if `allow_credentials` is ever needed in future (e.g., session cookies), requests will be blocked.

**Fix**: After deploying, update `ALLOWED_ORIGINS` in the Render dashboard or `render.yaml` to the production Vercel URL.

---

### BLOCKER 3 — `cryptography` not explicitly in `requirements.txt`

**Severity: High** (may surface as Blocker depending on Render's pip resolver)  
**Impact**: `bank_security.py` (bank token encryption) fails to import → bank sync endpoints return 500.

`cryptography` is currently available as a transitive dep (pulled in via `google-generativeai`), but this is fragile and version-dependent. It must be declared explicitly.

**Fix**: Add `cryptography>=41.0.0` to `backend/requirements.txt`.

---

## 6. Non-Blocking Improvements (Pre-Launch Recommended)

| # | Area | Finding | Recommendation |
|---|------|---------|----------------|
| 1 | `config.py` | `AVATAR_MAX_SIZE_BYTES` not a typed `Settings` field | Add `AVATAR_MAX_SIZE_BYTES: int = int(os.getenv("AVATAR_MAX_SIZE_BYTES", str(5*1024*1024)))` to `Settings` |
| 2 | `database/session.py` | No `pool_pre_ping` | Add `pool_pre_ping=True` to `create_engine()` for resilience on Render |
| 3 | `database/migrations.py` | No Alembic | Acceptable for current scale; plan Alembic migration for next major release |
| 4 | `config.py` | `SECRET_KEY` hardcoded fallback | Acceptable with `generateValue: true` in render.yaml; add startup validation warning log |
| 5 | `AuthContext.tsx` | `id` typed as `number` (line 5) but backend uses `String (UUID)` | Update `User.id` type to `string` in TypeScript interface |
| 6 | Token storage | `localStorage` used for JWT | Acceptable SPA pattern; document known XSS risk |
| 7 | Admin guard | `is_admin` check per route, not middleware | Low risk; document admin promotion mechanism |
| 8 | `docker-compose.yml` | Uses SQLite and dev `SECRET_KEY` | Add note that this is for local dev only |
| 9 | Root `.env.example` | Has duplicate content vs `backend/.env.example` | Consolidate or clarify which file is authoritative |
| 10 | ML model | `risk_model.pkl` committed to repo | Acceptable at this scale; consider DVC or model registry at scale |

---

## 7. External Integration Status

| Integration | Status | Notes |
|-------------|--------|-------|
| **Vercel** (frontend hosting) | ⚙️ Configured, not deployed | `vercel.json` and build commands ready |
| **Render** (backend hosting) | ⚙️ Configured, not deployed | `render.yaml` Blueprint ready (with blocker fixes) |
| **PostgreSQL on Render** | ⚙️ Configured | `finrisk-ai-db` defined in `render.yaml` |
| **SMTP / Email** | 🔴 Not configured | Requires real SMTP credentials in Render env vars |
| **Cloudflare R2 / S3** | 🔴 Not configured | Requires `AVATAR_STORAGE_BACKEND=s3` + credentials |
| **Google Gemini API** | 🟡 Optional | `GEMINI_API_KEY` empty; falls back to rule-based AI chat |
| **Plaid (live bank sync)** | 🔴 Not configured | Scaffold exists; `PLAID_CLIENT_ID` + `PLAID_SECRET` required for live sync |
| **Plaid Sandbox** | 🟡 Available | Set `PLAID_ENV=sandbox` with sandbox credentials to test |

---

## 8. Remediation Roadmap

### P0 — Must Fix Before Deployment (Blockers)

1. **Fix `render.yaml` buildCommand**:  
   Change `buildCommand: pip install -r requirements.txt`  
   → `buildCommand: pip install -r backend/requirements.txt`

2. **Add `cryptography` to `backend/requirements.txt`**:  
   Append `cryptography>=41.0.0`

3. **Configure `ALLOWED_ORIGINS`**:  
   After first Vercel deployment, set `ALLOWED_ORIGINS=https://<your-app>.vercel.app` in Render dashboard and redeploy.

4. **Set `VITE_API_BASE_URL`**:  
   In Vercel project settings → Environment Variables, add:  
   `VITE_API_BASE_URL=https://finrisk-ai-backend.onrender.com`

### P1 — Configure Before First User

5. **Configure SMTP** for password reset emails (Mailtrap for testing, SendGrid/Gmail for production).

6. **Set `FRONTEND_URL`** in Render to the production Vercel URL (used in reset email links).

7. **Configure S3/R2 storage** (or accept ephemeral avatars in free tier).

### P2 — Post-Launch Improvements

8. Add `pool_pre_ping=True` to `session.py` SQLAlchemy engine.
9. Fix `User.id` TypeScript type from `number` to `string` in `AuthContext.tsx`.
10. Add `AVATAR_MAX_SIZE_BYTES` as typed field in `config.py`.
11. Consider adding Plaid sandbox credentials for a live bank sync demo.

---

## 9. Deployment Checklist

Use this checklist for the first production deployment.

### Render (Backend)

- [ ] Apply P0 fix: change `buildCommand` in `render.yaml` to use `backend/requirements.txt`
- [ ] Apply P0 fix: add `cryptography>=41.0.0` to `backend/requirements.txt`
- [ ] Push changes to GitHub (Render Blueprint reads from repo)
- [ ] Connect Render to GitHub repository
- [ ] Create new Blueprint deployment using `render.yaml`
- [ ] Verify PostgreSQL database `finrisk-ai-db` is provisioned
- [ ] Verify `SECRET_KEY` was auto-generated (check service environment)
- [ ] Verify `/health` endpoint returns `200 OK`
- [ ] Set `ALLOWED_ORIGINS` to Vercel frontend URL
- [ ] Set `FRONTEND_URL` to Vercel frontend URL
- [ ] Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` (optional but required for password reset emails)
- [ ] Set `AVATAR_STORAGE_BACKEND=s3` and S3 credentials (optional but required for persistent avatars)
- [ ] Set `GEMINI_API_KEY` (optional — enables AI chat)

### Vercel (Frontend)

- [ ] Connect Vercel to GitHub repository
- [ ] Set Root Directory to `.` (root, not `frontend/`) — `vercel.json` at root handles everything
- [ ] Add Environment Variable: `VITE_API_BASE_URL=https://finrisk-ai-backend.onrender.com`
- [ ] Trigger production deployment
- [ ] Verify SPA routes work on direct URL access (e.g., visit `/dashboard` directly)
- [ ] Verify API calls reach the backend (check Network tab for 200s on `/api/me`)

### Post-Deployment Smoke Tests

- [ ] Register a new user
- [ ] Log in and verify JWT refresh works
- [ ] Request password reset (verify email received if SMTP configured)
- [ ] Add a transaction manually
- [ ] Upload a profile photo
- [ ] View the Dashboard, Analytics, and Insights pages
- [ ] Connect mock bank and verify transaction import
- [ ] Verify `/health` returns `{ "status": "ok" }` from production URL

---

## 10. Final Recommendation

**The project is NOT ready for immediate deployment in its current state, but it is very close.**

The core application is functionally complete and well-structured. The critical blockers are all configuration issues (not code defects) and can be resolved in under 30 minutes total.

**Recommended deployment sequence:**

1. Fix `render.yaml` buildCommand → `pip install -r backend/requirements.txt` (5 min)
2. Add `cryptography>=41.0.0` to `backend/requirements.txt` (2 min)
3. Deploy Render backend via Blueprint
4. Deploy Vercel frontend with `VITE_API_BASE_URL` env var
5. Set `ALLOWED_ORIGINS` in Render to the Vercel URL and redeploy backend (5 min)
6. Configure SMTP and `FRONTEND_URL` for password reset functionality

After those six steps, FinRisk AI will be fully operational in production.

---

*End of audit report. This document reflects a point-in-time read-only inspection. All findings are based on static code analysis and structural inspection — no production systems were accessed or modified.*
