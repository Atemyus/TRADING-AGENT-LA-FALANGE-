"""
Database models for persistent storage.
"""

import json
from datetime import datetime
from typing import Optional, List

from sqlalchemy import DateTime, String, Text, Boolean, Float, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


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
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Account identification
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Ultima Markets Demo", "IC Markets Live"
    broker_type: Mapped[str] = mapped_column(String(50), default="metaapi")  # "metaapi", "alpaca", etc.

    # MetaApi credentials
    metaapi_account_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metaapi_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Encrypted in production

    # Status
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    last_connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Trading configuration (stored as JSON strings)
    symbols_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # ["EUR/USD", "XAU/USD", ...]

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
    enabled_models_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    def symbols(self) -> List[str]:
        if self.symbols_json:
            return json.loads(self.symbols_json)
        return ["EUR/USD", "XAU/USD"]  # Default

    @symbols.setter
    def symbols(self, value: List[str]):
        self.symbols_json = json.dumps(value)

    @property
    def enabled_models(self) -> List[str]:
        if self.enabled_models_json:
            return json.loads(self.enabled_models_json)
        return ["chatgpt", "gemini", "grok", "qwen", "llama", "ernie", "kimi", "mistral"]

    @enabled_models.setter
    def enabled_models(self, value: List[str]):
        self.enabled_models_json = json.dumps(value)

    def __repr__(self) -> str:
        return f"<BrokerAccount(id={self.id}, name={self.name}, enabled={self.is_enabled})>"
