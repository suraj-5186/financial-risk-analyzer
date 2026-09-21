import logging
from sqlalchemy import inspect, text
from database.session import engine

logger = logging.getLogger("migrations")
logging.basicConfig(level=logging.INFO)

def run_migrations():
    """
    Idempotent, database-agnostic migration runner for SQLite and PostgreSQL.
    Ensures newly added columns and constraints exist before application queries execute.
    """
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    logger.info("Running database migrations check on tables: %s", tables)

    with engine.begin() as conn:
        # 1. Migrate income_sources
        if "income_sources" in tables:
            cols = [c["name"] for c in inspector.get_columns("income_sources")]
            if "income_type" not in cols:
                logger.info("Adding column 'income_type' to 'income_sources'")
                conn.execute(text("ALTER TABLE income_sources ADD COLUMN income_type VARCHAR(32) DEFAULT 'recurring'"))
                # Migrate any legacy 'one-time' frequencies
                conn.execute(text(
                    "UPDATE income_sources SET income_type = CASE "
                    "WHEN is_recurring = FALSE OR frequency = 'one-time' OR frequency = 'one_time' THEN 'one_time' "
                    "ELSE 'recurring' END"
                ))
            if "updated_at" not in cols:
                logger.info("Adding column 'updated_at' to 'income_sources'")
                conn.execute(text("ALTER TABLE income_sources ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))

        # 2. Migrate recommendations
        if "recommendations" in tables:
            cols = [c["name"] for c in inspector.get_columns("recommendations")]
            if "is_dismissed" not in cols:
                logger.info("Adding column 'is_dismissed' to 'recommendations'")
                conn.execute(text("ALTER TABLE recommendations ADD COLUMN is_dismissed BOOLEAN DEFAULT FALSE"))
            if "is_applied" not in cols:
                logger.info("Adding column 'is_applied' to 'recommendations'")
                conn.execute(text("ALTER TABLE recommendations ADD COLUMN is_applied BOOLEAN DEFAULT FALSE"))
            if "applied_at" not in cols:
                logger.info("Adding column 'applied_at' to 'recommendations'")
                conn.execute(text("ALTER TABLE recommendations ADD COLUMN applied_at TIMESTAMP NULL"))
            if "action_type" not in cols:
                logger.info("Adding column 'action_type' to 'recommendations'")
                conn.execute(text("ALTER TABLE recommendations ADD COLUMN action_type VARCHAR(64)"))
            if "action_payload" not in cols:
                logger.info("Adding column 'action_payload' to 'recommendations'")
                conn.execute(text("ALTER TABLE recommendations ADD COLUMN action_payload TEXT"))

            # Ensure unique index on user_id + id for concurrency protection
            indexes = [idx["name"] for idx in inspector.get_indexes("recommendations")]
            if "idx_recommendations_user_id_id" not in indexes:
                logger.info("Adding unique index 'idx_recommendations_user_id_id' to 'recommendations'")
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_recommendations_user_id_id ON recommendations(user_id, id)"))

        # 3. Migrate users for password_changed_at and token_version
        if "users" in tables:
            cols = [c["name"] for c in inspector.get_columns("users")]
            if "password_changed_at" not in cols:
                logger.info("Adding column 'password_changed_at' to 'users'")
                conn.execute(text("ALTER TABLE users ADD COLUMN password_changed_at TIMESTAMP NULL"))
            if "token_version" not in cols:
                logger.info("Adding column 'token_version' to 'users'")
                conn.execute(text("ALTER TABLE users ADD COLUMN token_version INTEGER DEFAULT 1"))

        # 4. Migrate password_reset_tokens indexes if table exists
        if "password_reset_tokens" in tables:
            indexes = [idx["name"] for idx in inspector.get_indexes("password_reset_tokens")]
            if "ix_password_reset_tokens_token_hash" not in indexes:
                logger.info("Adding unique index 'ix_password_reset_tokens_token_hash' to 'password_reset_tokens'")
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_password_reset_tokens_token_hash ON password_reset_tokens(token_hash)"))

        # 5. Migrate transactions table for auto-categorization metadata
        if "transactions" in tables:
            cols = [c["name"] for c in inspector.get_columns("transactions")]
            if "category_confidence" not in cols:
                logger.info("Adding column 'category_confidence' to 'transactions'")
                conn.execute(text("ALTER TABLE transactions ADD COLUMN category_confidence FLOAT DEFAULT 1.0"))
            if "auto_category" not in cols:
                logger.info("Adding column 'auto_category' to 'transactions'")
                conn.execute(text("ALTER TABLE transactions ADD COLUMN auto_category VARCHAR(64) NULL"))
            if "is_reviewed" not in cols:
                logger.info("Adding column 'is_reviewed' to 'transactions'")
                conn.execute(text("ALTER TABLE transactions ADD COLUMN is_reviewed BOOLEAN DEFAULT TRUE"))
            if "external_id" not in cols:
                logger.info("Adding column 'external_id' to 'transactions'")
                conn.execute(text("ALTER TABLE transactions ADD COLUMN external_id VARCHAR(128) NULL"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transactions_external_id ON transactions(external_id)"))
            if "bank_account_id" not in cols:
                logger.info("Adding column 'bank_account_id' to 'transactions'")
                conn.execute(text("ALTER TABLE transactions ADD COLUMN bank_account_id VARCHAR(64) NULL"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transactions_bank_account_id ON transactions(bank_account_id)"))
            if "source" not in cols:
                logger.info("Adding column 'source' to 'transactions'")
                conn.execute(text("ALTER TABLE transactions ADD COLUMN source VARCHAR(32) DEFAULT 'manual'"))
        # 6. Migrate recurring_payments table
        if "recurring_payments" not in tables:
            logger.info("Creating table 'recurring_payments'")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS recurring_payments (
                    id VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    merchant_name VARCHAR(255) NOT NULL,
                    normalized_name VARCHAR(255) NOT NULL,
                    category VARCHAR(64) NOT NULL DEFAULT 'Other',
                    frequency VARCHAR(32) NOT NULL,
                    average_amount FLOAT NOT NULL,
                    last_amount FLOAT NOT NULL,
                    estimated_monthly_cost FLOAT NOT NULL,
                    estimated_annual_cost FLOAT NOT NULL,
                    confidence FLOAT NOT NULL DEFAULT 0.7,
                    status VARCHAR(32) NOT NULL DEFAULT 'detected',
                    last_payment_date DATE NOT NULL,
                    next_estimated_date DATE NULL,
                    transaction_count INTEGER NOT NULL DEFAULT 2,
                    notes TEXT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_recurring_payments_user_id ON recurring_payments(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_recurring_payments_normalized_name ON recurring_payments(normalized_name)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_recurring_payments_user_norm ON recurring_payments(user_id, normalized_name)"))

        # 7. Migrate bank_connections and bank_accounts tables (Task 19)
        if "bank_connections" not in tables:
            logger.info("Creating table 'bank_connections'")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bank_connections (
                    id VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    provider VARCHAR(64) NOT NULL DEFAULT 'mock',
                    institution_id VARCHAR(128) NOT NULL,
                    institution_name VARCHAR(255) NOT NULL,
                    encrypted_access_token TEXT NOT NULL,
                    encrypted_refresh_token TEXT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'connected',
                    consent_expires_at TIMESTAMP NULL,
                    last_sync_at TIMESTAMP NULL,
                    sync_status VARCHAR(32) NOT NULL DEFAULT 'idle',
                    sync_error_message TEXT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bank_connections_user_id ON bank_connections(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bank_connections_user_status ON bank_connections(user_id, status)"))

        if "bank_accounts" not in tables:
            logger.info("Creating table 'bank_accounts'")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bank_accounts (
                    id VARCHAR(64) PRIMARY KEY,
                    connection_id VARCHAR(64) NOT NULL REFERENCES bank_connections(id) ON DELETE CASCADE,
                    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    external_account_id VARCHAR(128) NOT NULL,
                    account_name VARCHAR(255) NOT NULL,
                    account_type VARCHAR(64) NOT NULL DEFAULT 'depository',
                    account_subtype VARCHAR(64) NULL DEFAULT 'checking',
                    mask VARCHAR(16) NULL,
                    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
                    current_balance FLOAT NULL,
                    available_balance FLOAT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bank_accounts_connection_id ON bank_accounts(connection_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bank_accounts_user_id ON bank_accounts(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bank_accounts_external_id ON bank_accounts(external_account_id)"))

    logger.info("Database migrations check completed successfully.")

if __name__ == "__main__":
    run_migrations()
