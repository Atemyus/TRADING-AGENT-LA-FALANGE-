"""
Application configuration using Pydantic Settings.
All configuration is loaded from environment variables.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = Field(default="development", description="development|staging|production")
    DEBUG: bool = Field(default=True)

    # API
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = Field(default="change-me-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000", "http://127.0.0.1:3000"])

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/trading_db"
    )
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_MODEL_FAST: str = "gpt-4o-mini"

    # Broker Configuration
    BROKER_TYPE: str = Field(default="oanda", description="oanda|ig|interactive_brokers|alpaca")

    # OANDA
    OANDA_API_KEY: Optional[str] = None
    OANDA_ACCOUNT_ID: Optional[str] = None
    OANDA_ENVIRONMENT: str = Field(default="practice", description="practice|live")

    # IG Markets
    IG_API_KEY: Optional[str] = None
    IG_USERNAME: Optional[str] = None
    IG_PASSWORD: Optional[str] = None
    IG_ACCOUNT_ID: Optional[str] = None
    IG_ENVIRONMENT: str = Field(default="demo", description="demo|live")

    # Interactive Brokers
    IB_HOST: str = "127.0.0.1"
    IB_PORT: int = 7497  # 7497 for TWS paper, 7496 for live
    IB_CLIENT_ID: int = 1

    # Alpaca
    ALPACA_API_KEY: Optional[str] = None
    ALPACA_SECRET_KEY: Optional[str] = None
    ALPACA_PAPER: bool = True

    # Trading Configuration
    TRADING_ENABLED: bool = Field(default=False, description="Enable live trading")
    MAX_POSITIONS: int = 5
    MAX_DAILY_TRADES: int = 50
    MAX_DAILY_LOSS_PERCENT: float = 5.0
    DEFAULT_RISK_PER_TRADE: float = 1.0  # Percentage of account

    # Market Data
    CMC_API_KEY: Optional[str] = None

    # Notifications
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    DISCORD_WEBHOOK_URL: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
