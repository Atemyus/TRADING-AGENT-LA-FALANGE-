from abc import ABC, abstractmethod
from typing import Any


class BridgeProviderError(Exception):
    pass


class BaseTerminalProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def connect(
        self,
        *,
        login: str,
        password: str,
        server: str | None,
        platform: str,
        terminal_path: str | None = None,
        data_path: str | None = None,
        workspace_id: str | None = None,
        server_candidates: list[str] | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_account_info(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_positions(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def place_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_open_orders(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def close_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def modify_position(self, payload: dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_price(self, symbol: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_candles(
        self,
        *,
        symbol: str,
        timeframe: str,
        count: int,
        from_time: str | None = None,
        to_time: str | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError
