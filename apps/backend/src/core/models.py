"""
Database models for persistent storage.
"""

import json
import secrets
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class LicenseStatus(StrEnum):
    """License status enum."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


class WhopOrderStatus(StrEnum):
    """Whop order status enum."""
    PENDING = "pending"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    FAILED = "failed"


class WhopProduct(Base):
    """
    Whop product mapping to license configuration.
    Maps Whop product IDs to license settings.
    """
    __tablename__ = "whop_products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Whop product identification
    whop_product_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    whop_plan_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Product info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="EUR")

    # License configuration for this product
    license_duration_days: Mapped[int] = mapped_column(Integer, default=30)  # How long the license lasts
    license_max_uses: Mapped[int] = mapped_column(Integer, default=1)  # Max uses per license
    license_broker_slots: Mapped[int] = mapped_column(Integer, default=5)  # Broker/workspace slots for the license
    license_name_template: Mapped[str] = mapped_column(String(255), default="Whop License - {product_name}")

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    orders: Mapped[list["WhopOrder"]] = relationship("WhopOrder", back_populates="product")

    def __repr__(self) -> str:
        return f"<WhopProduct(id={self.id}, name={self.name}, whop_id={self.whop_product_id})>"


class WhopOrder(Base):
    """
    Whop order record.
    Stores all orders received from Whop webhooks.
    """
    __tablename__ = "whop_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Whop transaction identification
    whop_order_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    whop_membership_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    whop_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Customer info
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Product info
    product_id: Mapped[int | None] = mapped_column(ForeignKey("whop_products.id"), nullable=True)
    product: Mapped["WhopProduct | None"] = relationship("WhopProduct", back_populates="orders")
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Payment info
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="EUR")
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)  # card, paypal, crypto, etc.

    # Status
    status: Mapped[str] = mapped_column(String(20), default=WhopOrderStatus.PENDING)

    # License created from this order
    license_id: Mapped[int | None] = mapped_column(ForeignKey("licenses.id"), nullable=True)
    license: Mapped["License | None"] = relationship("License")
    license_created: Mapped[bool] = mapped_column(Boolean, default=False)

    # Raw webhook data (for debugging)
    raw_webhook_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    whop_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Notes from admin
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<WhopOrder(id={self.id}, whop_id={self.whop_order_id}, email={self.customer_email}, status={self.status})>"


class License(Base):
    """
    License model for access control.
    Each license can be used by one user and has an expiration date.
    """
    __tablename__ = "licenses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # License key - unique identifier
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    # License info
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # e.g., "Demo License", "Pro License"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default=LicenseStatus.ACTIVE)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Usage limits
    max_uses: Mapped[int] = mapped_column(Integer, default=1)  # How many users can use this license
    current_uses: Mapped[int] = mapped_column(Integer, default=0)
    broker_slots: Mapped[int] = mapped_column(Integer, default=5)  # How many broker workspaces are available

    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Audit
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Admin user ID
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship to users
    users: Mapped[list["User"]] = relationship("User", back_populates="license")

    @staticmethod
    def generate_key(prefix: str = "LIC") -> str:
        """Generate a unique license key."""
        # Format: LIC-XXXX-XXXX-XXXX-XXXX
        random_part = secrets.token_hex(16).upper()
        formatted = f"{prefix}-{random_part[:4]}-{random_part[4:8]}-{random_part[8:12]}-{random_part[12:16]}"
        return formatted

    @property
    def is_valid(self) -> bool:
        """Check if license is valid (active, not expired, has uses left)."""
        if not self.is_active or self.status != LicenseStatus.ACTIVE:
            return False
        if self.expires_at and self.expires_at < datetime.now(self.expires_at.tzinfo):
            return False
        if self.current_uses >= self.max_uses:
            return False
        return True

    @property
    def is_expired(self) -> bool:
        """Check if license has expired."""
        if self.expires_at:
            from datetime import UTC
            return self.expires_at < datetime.now(UTC)
        return False

    def __repr__(self) -> str:
        return f"<License(id={self.id}, key={self.key[:12]}..., status={self.status})>"


class User(Base):
    """
    User model for authentication.
    Stores user credentials and profile information.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # License
    license_id: Mapped[int | None] = mapped_column(ForeignKey("licenses.id"), nullable=True)
    license_activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    license: Mapped["License | None"] = relationship("License", back_populates="users")
    broker_accounts: Mapped[list["BrokerAccount"]] = relationship("BrokerAccount", back_populates="user")

    # Email verification
    verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verification_token_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Password reset
    reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"


class AppSettings(Base):
    """
    Persistent application settings stored in database.
    Uses key-value format for flexibility.
    """
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<AppSettings(key={self.key})>"


class BrokerAccount(Base):
    """
    Broker account configuration for multi-broker support.
    Each account has its own symbols, risk settings, and runs independently.
    """
    __tablename__ = "broker_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "slot_index", name="uq_broker_accounts_user_slot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user: Mapped["User | None"] = relationship("User", back_populates="broker_accounts")
    slot_index: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-based slot index within the license

    # Account identification
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Ultima Markets Demo", "IC Markets Live"
    broker_type: Mapped[str] = mapped_column(String(50), default="metaapi")  # "metaapi", "alpaca", etc.
    broker_catalog_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    platform_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # MetaApi credentials
    metaapi_account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metaapi_token: Mapped[str | None] = mapped_column(Text, nullable=True)  # Encrypted in production
    credentials_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Trading configuration (stored as JSON strings)
    symbols_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # ["EUR/USD", "XAU/USD", ...]

    # Risk settings
    risk_per_trade_percent: Mapped[float] = mapped_column(Float, default=1.0)
    max_open_positions: Mapped[int] = mapped_column(Integer, default=3)
    max_daily_trades: Mapped[int] = mapped_column(Integer, default=10)
    max_daily_loss_percent: Mapped[float] = mapped_column(Float, default=5.0)

    # Analysis settings
    analysis_mode: Mapped[str] = mapped_column(String(20), default="standard")  # quick, standard, premium, ultra
    analysis_interval_seconds: Mapped[int] = mapped_column(Integer, default=300)
    min_confidence: Mapped[float] = mapped_column(Float, default=75.0)
    min_models_agree: Mapped[int] = mapped_column(Integer, default=4)

    # AI models (stored as JSON)
    enabled_models_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Trading hours
    trading_start_hour: Mapped[int] = mapped_column(Integer, default=7)
    trading_end_hour: Mapped[int] = mapped_column(Integer, default=21)
    trade_on_weekends: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Properties for JSON fields
    @property
    def symbols(self) -> list[str]:
        if self.symbols_json:
            return json.loads(self.symbols_json)
        return ["EUR/USD", "XAU/USD"]  # Default

    @symbols.setter
    def symbols(self, value: list[str]):
        self.symbols_json = json.dumps(value)

    @property
    def enabled_models(self) -> list[str]:
        if self.enabled_models_json:
            return json.loads(self.enabled_models_json)
        return ["chatgpt", "gemini", "grok", "qwen", "llama", "ernie", "kimi", "mistral"]

    @enabled_models.setter
    def enabled_models(self, value: list[str]):
        self.enabled_models_json = json.dumps(value)

    @property
    def credentials(self) -> dict[str, str]:
        if self.credentials_json:
            try:
                data = json.loads(self.credentials_json)
                if isinstance(data, dict):
                    return {str(k): str(v) for k, v in data.items() if v is not None}
            except Exception:
                pass
        return {}

    @credentials.setter
    def credentials(self, value: dict[str, str]):
        self.credentials_json = json.dumps(value or {})

    def __repr__(self) -> str:
        return f"<BrokerAccount(id={self.id}, name={self.name}, enabled={self.is_enabled})>"
