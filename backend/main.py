import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database.session import engine
from models.base import Base

# Import all models to ensure they register correctly before metadata creation
from models.user import User
from models.profile import FinancialProfile
from models.budget import Budget
from models.goal import FinancialGoal
from models.transaction import Transaction
from models.notification import Notification
from models.prediction import Prediction
from models.recommendation import Recommendation
from models.report import Report
from models.chat import ChatHistory
from models.settings import UserSettings
from models.audit import AuditLog
from models.income_source import IncomeSource
from models.income_allocation import IncomeAllocation
from models.password_reset import PasswordResetToken
from models.recurring_payment import RecurringPayment
from models.bank_connection import BankConnection
from models.bank_account import BankAccount

# Initialize tables
Base.metadata.create_all(bind=engine)

# Run idempotent schema migrations
from database.migrations import run_migrations
run_migrations()

# Import routers
from routers import auth, profile, budget, goal, transaction, user, notification, admin, report, chat, forecast, audit, recurring, bank_sync, insights
from routers.income import router as income_router
from routers.settings import router as settings_router
from routers.recommendation import router as recommendation_router
import os
from fastapi.staticfiles import StaticFiles

app = FastAPI(title=settings.PROJECT_NAME)

# Create upload directory and mount StaticFiles
upload_base = "/tmp" if os.getenv("VERCEL") else os.path.join(os.path.dirname(__file__), "..")
UPLOAD_DIR = os.path.abspath(os.path.join(upload_base, "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "avatars"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# CORS configuration
# Resolves allowed origins and credentials safely.
# Production never falls back to wildcard (*); local dev defaults to localhost origins.
from config import resolve_cors_origins

ALLOWED_ORIGINS, ALLOW_CREDENTIALS = resolve_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(budget.router)
app.include_router(goal.router)
app.include_router(transaction.router)
app.include_router(transaction.risk_router)
app.include_router(user.router)
app.include_router(notification.router)
app.include_router(admin.router)
app.include_router(report.router)
app.include_router(chat.router)
app.include_router(forecast.router)
app.include_router(settings_router)
app.include_router(audit.router)
app.include_router(income_router)
app.include_router(recommendation_router)
app.include_router(recurring.router)
app.include_router(bank_sync.router)
app.include_router(insights.router)

@app.get("/")
def read_root():
    return {"status": "healthy", "project": settings.PROJECT_NAME}

@app.get("/health")
def health_check():
    """Lightweight health endpoint used by Render's health checks."""
    return {"status": "ok"}
