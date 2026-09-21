import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from models.base import Base


class BankConnection(Base):
    __tablename__ = "bank_connections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(64), nullable=False, default="mock")
    institution_id = Column(String(128), nullable=False)
    institution_name = Column(String(255), nullable=False)
    encrypted_access_token = Column(Text, nullable=False)
    encrypted_refresh_token = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="connected")  # connected, syncing, error, disconnected
    consent_expires_at = Column(DateTime, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    sync_status = Column(String(32), nullable=False, default="idle")  # idle, success, failed
    sync_error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="bank_connections")
    accounts = relationship("BankAccount", back_populates="connection", cascade="all, delete-orphan")
