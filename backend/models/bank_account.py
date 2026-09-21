import datetime
import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from models.base import Base


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    connection_id = Column(String, ForeignKey("bank_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    external_account_id = Column(String(128), nullable=False, index=True)
    account_name = Column(String(255), nullable=False)
    account_type = Column(String(64), nullable=False, default="depository")  # depository, credit, investment, loan
    account_subtype = Column(String(64), nullable=True, default="checking")  # checking, savings, credit_card
    mask = Column(String(16), nullable=True)  # Last 4 digits only, never full account number
    currency = Column(String(10), nullable=False, default="INR")
    current_balance = Column(Float, nullable=True)
    available_balance = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    connection = relationship("BankConnection", back_populates="accounts")
    user = relationship("User", back_populates="bank_accounts")
    transactions = relationship("Transaction", back_populates="bank_account")
