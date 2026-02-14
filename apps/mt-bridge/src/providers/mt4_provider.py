from typing import Any
from urllib.parse import quote_plus, urljoin

import httpx

from src.config import BridgeSettings

from .base import BaseTerminalProvider, BridgeProviderError


def _pick(payload: Any, keys: list[str], default: Any = None) -> Any:
    if not isinstance(payload, dict):
        return default
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return default


class MT4TerminalProvider(BaseTerminalProvider):
    """
    MT4 provider via external adapter endpoint.

    Why adapter:
    - There is no official MT4 Python package equivalent to MetaTrader5.
    - A terminal-side bridge/EA (or local node agent) exposes HTTP endpoints
      and this provider delegates all account/trading operations to it.
    """

    def __init__(self, *, settings: BridgeSettings):
        self._settings = settings
        self._connected = False
        self._base_url = (settings.MT_BRIDGE_MT4_ADAPTER_BASE_URL or "").strip().rstrip("/")
        self._api_key = (settings.MT_BRIDGE_MT4_ADAPTER_API_KEY or "").strip() or None
        self._timeout = max(float(settings.MT_BRIDGE_MT4_ADAPTER_TIMEOUT_SECONDS), 5.0)
        self._session_id: str | None = None
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "mt4"

    def _ensure_base_url(self) -> str:
        if not self._base_url:
            raise BridgeProviderError(
                "MT4 adapter base URL not configured. "
                "Set MT_BRIDGE_MT4_ADAPTER_BASE_URL in bridge node environment."
            )
        value = self._base_url
        if not value.startswith(("http://", "https://")):
            value = f"http://{value}"
        return value

    async def _ensure_client(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                verify=False,
            )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
            headers["X-Bridge-Key"] = self._api_key
        return headers

    def _url(self, endpoint: str) -> str:
        return urljoin(f"{self._ensure_base_url()}/", endpoint.lstrip("/"))

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        await self._ensure_client()
        if not self._client:
            raise BridgeProviderError("MT4 adapter client not initialized")

        response = await self._client.request(
            method=method.upper(),
            url=self._url(endpoint),
            headers=self._headers(),
            params=params,
            json=data,
        )
        if response.status_code >= 400:
            detail = response.text.strip()[:300]
            raise BridgeProviderError(
                f"MT4 adapter request failed ({response.status_code}): {detail}"
            )
        if not response.content:
            return {}
        try:
            return response.json()
        except Exception:
            return {"raw": response.text}

    def _session_endpoint(self, template: str) -> str:
        if not self._session_id:
            raise BridgeProviderError("MT4 adapter session not connected")
        return template.replace("{session_id}", quote_plus(self._session_id))

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
        _ = platform
        payload: dict[str, Any] = {
            "platform": "mt4",
            "login": login,
            "account_number": login,
            "password": password,
            "server": server,
            "server_name": server,
        }
        if terminal_path:
            payload["terminal_path"] = terminal_path
        if data_path:
            payload["data_path"] = data_path
        if workspace_id:
            payload["workspace_id"] = workspace_id

        response = await self._request("POST", "/api/v1/sessions/connect", data=payload)
        session_id = str(_pick(response, ["session_id", "sessionId", "id"], "") or "").strip()
        if not session_id:
            raise BridgeProviderError("MT4 adapter connect response missing session_id")
        self._session_id = session_id
        self._connected = True

    async def disconnect(self) -> None:
        if self._session_id:
            try:
                await self._request(
                    "POST",
                    self._session_endpoint("/api/v1/sessions/{session_id}/disconnect"),
                    data={"session_id": self._session_id},
                )
            except Exception:
                pass
        if self._client:
            await self._client.aclose()
            self._client = None
        self._session_id = None
        self._connected = False

    async def get_account_info(self) -> dict[str, Any]:
        return await self._request(
            "GET",
            self._session_endpoint("/api/v1/sessions/{session_id}/account"),
        )

    async def get_positions(self) -> list[dict[str, Any]]:
        payload = await self._request(
            "GET",
            self._session_endpoint("/api/v1/sessions/{session_id}/positions"),
        )
        if isinstance(payload, list):
            return payload
        rows = _pick(payload, ["positions", "items", "data"], [])
        return rows if isinstance(rows, list) else []

    async def place_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = await self._request(
            "POST",
            self._session_endpoint("/api/v1/sessions/{session_id}/orders"),
            data=payload,
        )
        return result if isinstance(result, dict) else {"raw": result}

    async def get_open_orders(self) -> list[dict[str, Any]]:
        payload = await self._request(
            "GET",
            self._session_endpoint("/api/v1/sessions/{session_id}/orders/open"),
        )
        if isinstance(payload, list):
            return payload
        rows = _pick(payload, ["orders", "items", "data"], [])
        return rows if isinstance(rows, list) else []

    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        payload = await self._request(
            "GET",
            self._session_endpoint(f"/api/v1/sessions/{{session_id}}/orders/{quote_plus(str(order_id))}"),
        )
        return payload if isinstance(payload, dict) else None

    async def cancel_order(self, order_id: str) -> bool:
        await self._request(
            "DELETE",
            self._session_endpoint(f"/api/v1/sessions/{{session_id}}/orders/{quote_plus(str(order_id))}"),
        )
        return True

    async def close_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = await self._request(
            "POST",
            self._session_endpoint("/api/v1/sessions/{session_id}/positions/close"),
            data=payload,
        )
        return result if isinstance(result, dict) else {"raw": result}

    async def modify_position(self, payload: dict[str, Any]) -> bool:
        await self._request(
            "POST",
            self._session_endpoint("/api/v1/sessions/{session_id}/positions/modify"),
            data=payload,
        )
        return True

    async def get_price(self, symbol: str) -> dict[str, Any]:
        payload = await self._request(
            "GET",
            self._session_endpoint(f"/api/v1/sessions/{{session_id}}/prices/{quote_plus(symbol)}"),
        )
        return payload if isinstance(payload, dict) else {"raw": payload}

    async def get_candles(
        self,
        *,
        symbol: str,
        timeframe: str,
        count: int,
        from_time: str | None = None,
        to_time: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "timeframe": timeframe,
            "count": max(1, min(int(count or 100), 2000)),
        }
        if from_time:
            params["from"] = from_time
        if to_time:
            params["to"] = to_time
        payload = await self._request(
            "GET",
            self._session_endpoint(f"/api/v1/sessions/{{session_id}}/candles/{quote_plus(symbol)}"),
            params=params,
        )
        if isinstance(payload, list):
            return payload
        rows = _pick(payload, ["candles", "bars", "items", "data"], [])
        return rows if isinstance(rows, list) else []
