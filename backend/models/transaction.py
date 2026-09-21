import datetime
import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Date, Boolean
from sqlalchemy.orm import relationship
from models.base import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False) # "Income" or "Expense"
    category = Column(String, nullable=False)
    category_confidence = Column(Float, nullable=True, default=1.0)
    auto_category = Column(String, nullable=True)
    is_reviewed = Column(Boolean, default=True, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    transaction_date = Column(Date, nullable=False, default=datetime.date.today)
    payment_method = Column(String, nullable=False) # Cash, Card, UPI, etc.
    # Bank Synchronization fields (Task 19)
    external_id = Column(String(128), nullable=True, index=True) # Provider transaction ID
    bank_account_id = Column(String, ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    source = Column(String(32), nullable=False, default="manual") # manual, csv_import, bank_sync
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="transactions")
    bank_account = relationship("BankAccount", back_populates="transactions")
