from typing import Any

from .base import BaseTerminalProvider, BridgeProviderError


class MT4TerminalProvider(BaseTerminalProvider):
    """
    Placeholder MT4 provider.

    MT4 bridge execution usually needs a custom terminal-side EA/plugin.
    This provider is intentionally explicit until that adapter is implemented.
    """

    @property
    def name(self) -> str:
        return "mt4"

    async def connect(
        self,
        *,
        login: str,
        password: str,
        server: str,
        platform: str,
        terminal_path: str | None = None,
        data_path: str | None = None,
        workspace_id: str | None = None,
    ) -> None:
        _ = login, password, server, platform, terminal_path, data_path, workspace_id
        raise BridgeProviderError(
            "MT4 provider not implemented in this MVP bridge node. "
            "Use MT5 provider mode or implement MT4 terminal adapter."
        )

    async def disconnect(self) -> None:
        return

    async def get_account_info(self) -> dict[str, Any]:
        raise BridgeProviderError("MT4 provider not implemented")

    async def get_positions(self) -> list[dict[str, Any]]:
        raise BridgeProviderError("MT4 provider not implemented")

    async def place_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        _ = payload
        raise BridgeProviderError("MT4 provider not implemented")

    async def get_open_orders(self) -> list[dict[str, Any]]:
        raise BridgeProviderError("MT4 provider not implemented")

    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        _ = order_id
        raise BridgeProviderError("MT4 provider not implemented")

    async def cancel_order(self, order_id: str) -> bool:
        _ = order_id
        raise BridgeProviderError("MT4 provider not implemented")

    async def close_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        _ = payload
        raise BridgeProviderError("MT4 provider not implemented")

    async def modify_position(self, payload: dict[str, Any]) -> bool:
        _ = payload
        raise BridgeProviderError("MT4 provider not implemented")

    async def get_price(self, symbol: str) -> dict[str, Any]:
        _ = symbol
        raise BridgeProviderError("MT4 provider not implemented")

    async def get_candles(
        self,
        *,
        symbol: str,
        timeframe: str,
        count: int,
        from_time: str | None = None,
        to_time: str | None = None,
    ) -> list[dict[str, Any]]:
        _ = symbol, timeframe, count, from_time, to_time
        raise BridgeProviderError("MT4 provider not implemented")
