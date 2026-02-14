from src.config import BridgeSettings

from .base import BaseTerminalProvider, BridgeProviderError
from .mock_provider import MockTerminalProvider
from .mt4_provider import MT4TerminalProvider
from .mt5_provider import MT5TerminalProvider


def create_provider(*, platform: str, settings: BridgeSettings) -> BaseTerminalProvider:
    mode = (settings.MT_BRIDGE_PROVIDER_MODE or "mock").strip().lower()
    safe_platform = (platform or settings.MT_BRIDGE_DEFAULT_PLATFORM or "mt5").strip().lower()

    if mode == "mock":
        return MockTerminalProvider()
    if mode == "mt5":
        if safe_platform == "mt4":
            return MT4TerminalProvider(settings=settings)
        return MT5TerminalProvider()
    raise BridgeProviderError(
        f"Unsupported provider mode '{mode}'. Allowed: mock|mt5"
    )


__all__ = [
    "BaseTerminalProvider",
    "BridgeProviderError",
    "create_provider",
]
