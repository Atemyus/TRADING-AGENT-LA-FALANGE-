"""
Application configuration using Pydantic Settings.
All configuration is loaded from environment variables.
"""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_CONFIG_PATH = Path(__file__).resolve()
_CONFIG_PARENTS = tuple(_CONFIG_PATH.parents)


def _resolve_backend_dir() -> Path:
    """
    Resolve backend root directory in a layout-agnostic way.

    Works for both:
    - local repo: <repo>/apps/backend/src/core/config.py
    - container: /app/src/core/config.py
    """
    for candidate in (_CONFIG_PATH.parent, *_CONFIG_PARENTS):
        if (candidate / "src" / "core").is_dir():
            return candidate

    # Fallback to historical relative position when structure is unexpected.
    return _CONFIG_PARENTS[min(2, len(_CONFIG_PARENTS) - 1)]


def _resolve_repo_root(backend_dir: Path) -> Path:
    """Resolve repository root when backend lives under <repo>/apps/backend."""
    if backend_dir.parent.name == "apps":
        return backend_dir.parent.parent
    return backend_dir


_BACKEND_DIR = _resolve_backend_dir()
_REPO_ROOT = _resolve_repo_root(_BACKEND_DIR)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        # Support both local backend `.env` and repository-root `.env`.
        env_file=(
            str(_BACKEND_DIR / ".env"),
            str(_REPO_ROOT / ".env"),
            ".env",
        ),
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
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS string into a list."""
        def normalize_origin(origin: str) -> str:
            return origin.strip().rstrip("/")

        v = self.CORS_ORIGINS
        if not v:
            return ["*"]
        # Handle JSON array format
        if v.startswith("["):
            try:
                origins = json.loads(v)
                if isinstance(origins, list):
                    return [o for o in (normalize_origin(str(origin)) for origin in origins) if o]
                return ["*"]
            except json.JSONDecodeError:
                pass
        # Handle "*" wildcard
        if v.strip() == "*":
            return ["*"]
        # Handle comma-separated list
        return [o for o in (normalize_origin(origin) for origin in v.split(",")) if o]

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
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_MODEL_FAST: str = "gpt-4o-mini"

    # Anthropic (Claude)
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # Google (Gemini)
    GOOGLE_API_KEY: str | None = None
    GOOGLE_MODEL: str = "gemini-1.5-flash"

    # Groq (Ultra-fast inference)
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Mistral
    MISTRAL_API_KEY: str | None = None
    MISTRAL_MODEL: str = "mistral-large-latest"

    # Ollama (Local inference)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"

    # AIML API (Multi-model gateway)
    AIML_API_KEY: str | None = None
    AIML_BASE_URL: str = "https://api.aimlapi.com/v1"

    # NVIDIA API (Kimi K2.5, Mistral Large 3)
    NVIDIA_API_KEY: str | None = None
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    # Alpha Vantage (Market Data)
    ALPHA_VANTAGE_API_KEY: str | None = None

    # Broker Configuration
    BROKER_TYPE: str = Field(default="none", description="none|oanda|metatrader|ig|interactive_brokers|alpaca")

    # OANDA
    OANDA_API_KEY: str | None = None
    OANDA_ACCOUNT_ID: str | None = None
    OANDA_ENVIRONMENT: str = Field(default="practice", description="practice|live")

    # MetaTrader (via MetaApi.cloud)
    METAAPI_ACCESS_TOKEN: str | None = None
    METAAPI_ACCOUNT_ID: str | None = None

    # MetaTrader connection mode
    # metaapi: existing MetaApi cloud integration
    # bridge: custom self-hosted bridge service (MT terminal nodes)
    METATRADER_CONNECTION_MODE: str = Field(default="metaapi", description="metaapi|bridge")
    MT_BRIDGE_BASE_URL: str | None = None
    MT_BRIDGE_API_KEY: str | None = None
    MT_BRIDGE_TIMEOUT_SECONDS: float = 90.0

    # IG Markets
    IG_API_KEY: str | None = None
    IG_USERNAME: str | None = None
    IG_PASSWORD: str | None = None
    IG_ACCOUNT_ID: str | None = None
    IG_ENVIRONMENT: str = Field(default="demo", description="demo|live")

    # Interactive Brokers
    IB_HOST: str = "127.0.0.1"
    IB_PORT: int = 7497  # 7497 for TWS paper, 7496 for live
    IB_CLIENT_ID: int = 1

    # Alpaca
    ALPACA_API_KEY: str | None = None
    ALPACA_SECRET_KEY: str | None = None
    ALPACA_PAPER: bool = True

    # Trading Configuration
    TRADING_ENABLED: bool = Field(default=False, description="Enable live trading")
    MAX_POSITIONS: int = 5
    MAX_DAILY_TRADES: int = 50
    MAX_DAILY_LOSS_PERCENT: float = 5.0
    DEFAULT_RISK_PER_TRADE: float = 1.0  # Percentage of account

    # Market Data
    CMC_API_KEY: str | None = None

    # Email Service (Resend)
    RESEND_API_KEY: str | None = None
    EMAIL_FROM: str | None = None
    FRONTEND_URL: str = "http://localhost:3000"

    # Bootstrap admin (optional, for first-time production setup)
    ADMIN_EMAIL: str | None = None
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str | None = None
    ADMIN_FULL_NAME: str | None = None

    # Optional bootstrap license for registration tests
    BOOTSTRAP_LICENSE_KEY: str | None = None
    BOOTSTRAP_LICENSE_NAME: str = "Bootstrap License"
    BOOTSTRAP_LICENSE_MAX_USES: int = 100
    BOOTSTRAP_LICENSE_BROKER_SLOTS: int = 5
    BOOTSTRAP_LICENSE_DURATION_DAYS: int = 365

    # Notifications
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None
    DISCORD_WEBHOOK_URL: str | None = None

    # Whop Integration
    WHOP_API_KEY: str | None = None
    WHOP_WEBHOOK_SECRET: str | None = None
    WHOP_COMPANY_ID: str | None = None


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
