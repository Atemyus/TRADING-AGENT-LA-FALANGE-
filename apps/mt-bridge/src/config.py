from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BridgeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MT_BRIDGE_HOST: str = "0.0.0.0"
    MT_BRIDGE_PORT: int = 9000
    MT_BRIDGE_API_KEY: str | None = None
    MT_BRIDGE_PROVIDER_MODE: str = Field(default="mock", description="mock|mt5")
    MT_BRIDGE_DEFAULT_PLATFORM: str = Field(default="mt5", description="mt4|mt5")
    MT_BRIDGE_MAX_SESSIONS: int = 20
    MT_BRIDGE_TERMINAL_AUTO_LAUNCH: bool = False
    MT_BRIDGE_TERMINAL_SHUTDOWN_ON_DISCONNECT: bool = True
    MT_BRIDGE_TERMINAL_LAUNCH_TIMEOUT_SECONDS: float = 10.0
    MT_BRIDGE_TERMINAL_DEFAULT_ARGUMENTS: str | None = None
    MT_BRIDGE_MT4_ADAPTER_BASE_URL: str | None = None
    MT_BRIDGE_MT4_ADAPTER_API_KEY: str | None = None
    MT_BRIDGE_MT4_ADAPTER_TIMEOUT_SECONDS: float = 20.0


@lru_cache
def get_settings() -> BridgeSettings:
    return BridgeSettings()
