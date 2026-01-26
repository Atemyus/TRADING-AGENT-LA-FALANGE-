"""
Application configuration using Pydantic Settings.
All configuration is loaded from environment variables.
"""

import json
from functools import lru_cache
from typing import List, Optional, Union

from pydantic import Field, field_validator, computed_field
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

    # CORS - stored as string, parsed to list via property
    CORS_ORIGINS: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")

    @computed_field
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list."""
        v = self.CORS_ORIGINS
        if not v:
            return ["*"]
        # Handle JSON array format
        if v.startswith("["):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        # Handle "*" wildcard
        if v.strip() == "*":
            return ["*"]
        # Handle comma-separated list
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/trading_db"
    )
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # AI Providers
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_MODEL_FAST: str = "gpt-4o-mini"

    # Anthropic (Claude)
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # Google (Gemini)
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_MODEL: str = "gemini-1.5-flash"

    # Groq (Ultra-fast inference)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Mistral
    MISTRAL_API_KEY: Optional[str] = None
    MISTRAL_MODEL: str = "mistral-large-latest"

    # Ollama (Local inference)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"

    # AIML API (Multi-model gateway)
    AIML_API_KEY: Optional[str] = None
    AIML_BASE_URL: str = "https://api.aimlapi.com/v1"

    # Alpha Vantage (Market Data)
    ALPHA_VANTAGE_API_KEY: Optional[str] = None

    # Broker Configuration
    BROKER_TYPE: str = Field(default="none", description="none|oanda|metatrader|ig|interactive_brokers|alpaca")

    # OANDA
    OANDA_API_KEY: Optional[str] = None
    OANDA_ACCOUNT_ID: Optional[str] = None
    OANDA_ENVIRONMENT: str = Field(default="practice", description="practice|live")

    # MetaTrader (via MetaApi.cloud)
    METAAPI_ACCESS_TOKEN: Optional[str] = None
    METAAPI_ACCOUNT_ID: Optional[str] = None

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


def clear_settings_cache() -> None:
    """Clear the settings cache to force reload from environment."""
    get_settings.cache_clear()
    global settings
    settings = get_settings()


settings = get_settings()
