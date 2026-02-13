"""
Generic Platform REST Broker

Reusable broker adapter for platforms exposing HTTP APIs with:
- account/password/server authentication
- account/positions/orders endpoints
- quote and candle endpoints

Used for: cTrader, DXtrade, MatchTrader.
"""

import asyncio
import base64
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote_plus, urljoin

import httpx

from src.engines.trading.base_broker import (
    AccountInfo,
    BaseBroker,
    Candle,
    Instrument,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    PositionSide,
    Tick,
    TimeInForce,
)


def _to_decimal(value: Any, fallback: str = "0") -> Decimal:
    try:
        if value is None or value == "":
            return Decimal(fallback)
        return Decimal(str(value))
    except Exception:
        return Decimal(fallback)


def _to_float(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return fallback
        return float(value)
    except Exception:
        return fallback


def _to_int(value: Any, fallback: int = 1) -> int:
    try:
        if value is None or value == "":
            return fallback
        return int(value)
    except Exception:
        return fallback


def _parse_timestamp(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        return datetime.now(UTC)
    for candidate in (
        text.replace("Z", "+00:00"),
        text.replace("/", "-"),
    ):
        try:
            return datetime.fromisoformat(candidate)
        except Exception:
            continue
    for fmt in ("%Y:%m:%d-%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except Exception:
            continue
    return datetime.now(UTC)


def _nested_get(payload: Any, path: str) -> Any:
    if not path:
        return None
    current = payload
    for key in path.split("."):
        if isinstance(current, dict) and key in current:
            current = current[key]
            continue
        return None
    return current


def _pick(payload: Any, keys: list[str], default: Any = None) -> Any:
    if not isinstance(payload, dict):
        return default
    for key in keys:
        if "." in key:
            value = _nested_get(payload, key)
        else:
            value = payload.get(key)
        if value is not None:
            return value
    return default


def _coerce_side(value: str | None) -> PositionSide:
    text = (value or "").lower()
    if text in {"sell", "short"}:
        return PositionSide.SHORT
    return PositionSide.LONG


def _coerce_order_side(value: str | None) -> OrderSide:
    text = (value or "").lower()
    if text in {"sell", "short"}:
        return OrderSide.SELL
    return OrderSide.BUY


def _coerce_order_type(value: str | None) -> OrderType:
    text = (value or "").lower()
    if text == "limit":
        return OrderType.LIMIT
    if text == "stop":
        return OrderType.STOP
    if text in {"stop_limit", "stoplimit"}:
        return OrderType.STOP_LIMIT
    return OrderType.MARKET


def _coerce_order_status(value: str | None) -> OrderStatus:
    text = (value or "").lower()
    if text in {"filled", "executed", "accepted", "done", "closed"}:
        return OrderStatus.FILLED
    if text in {"partially_filled", "partial", "partial_fill"}:
        return OrderStatus.PARTIALLY_FILLED
    if text in {"cancelled", "canceled", "deleted"}:
        return OrderStatus.CANCELLED
    if text in {"rejected", "denied"}:
        return OrderStatus.REJECTED
    if text in {"expired"}:
        return OrderStatus.EXPIRED
    return OrderStatus.PENDING


class PlatformRestBroker(BaseBroker):
    """Generic HTTP broker adapter with configurable endpoints."""

    DEFAULT_ENDPOINTS: dict[str, dict[str, str]] = {
        "ctrader": {
            "login_endpoint": "/connect/token",
            "health_endpoint": "/",
            "account_endpoint": "/api/account",
            "positions_endpoint": "/api/positions",
            "symbols_endpoint": "/api/symbols",
            "place_order_endpoint": "/api/orders",
            "orders_endpoint": "/api/orders",
            "order_endpoint_template": "/api/orders/{order_id}",
            "cancel_order_endpoint_template": "/api/orders/{order_id}",
            "close_position_endpoint_template": "/api/positions/{position_id}/close",
            "close_position_by_symbol_endpoint": "/api/positions/close",
            "modify_position_endpoint_template": "/api/positions/{position_id}",
            "price_endpoint_template": "/api/prices/{symbol}",
            "prices_endpoint": "/api/prices",
            "candles_endpoint_template": "/api/candles/{symbol}",
        },
        "dxtrade": {
            "login_endpoint": "/api/auth/login",
            "health_endpoint": "/api/health",
            "account_endpoint": "/api/v1/account",
            "positions_endpoint": "/api/v1/positions",
            "symbols_endpoint": "/api/v1/symbols",
            "place_order_endpoint": "/api/v1/orders",
            "orders_endpoint": "/api/v1/orders",
            "order_endpoint_template": "/api/v1/orders/{order_id}",
            "cancel_order_endpoint_template": "/api/v1/orders/{order_id}",
            "close_position_endpoint_template": "/api/v1/positions/{position_id}/close",
            "close_position_by_symbol_endpoint": "/api/v1/positions/close",
            "modify_position_endpoint_template": "/api/v1/positions/{position_id}",
            "price_endpoint_template": "/api/v1/prices/{symbol}",
            "prices_endpoint": "/api/v1/prices",
            "candles_endpoint_template": "/api/v1/candles/{symbol}",
        },
        "matchtrader": {
            "login_endpoint": "/api/login",
            "health_endpoint": "/api/health",
            "account_endpoint": "/api/account",
            "positions_endpoint": "/api/positions",
            "symbols_endpoint": "/api/symbols",
            "place_order_endpoint": "/api/orders",
            "orders_endpoint": "/api/orders",
            "order_endpoint_template": "/api/orders/{order_id}",
            "cancel_order_endpoint_template": "/api/orders/{order_id}",
            "close_position_endpoint_template": "/api/positions/{position_id}/close",
            "close_position_by_symbol_endpoint": "/api/positions/close",
            "modify_position_endpoint_template": "/api/positions/{position_id}",
            "price_endpoint_template": "/api/prices/{symbol}",
            "prices_endpoint": "/api/prices",
            "candles_endpoint_template": "/api/candles/{symbol}",
        },
    }

    DEFAULT_METHODS = {
        "login_method": "POST",
        "account_method": "GET",
        "positions_method": "GET",
        "symbols_method": "GET",
        "place_order_method": "POST",
        "orders_method": "GET",
        "order_method": "GET",
        "cancel_order_method": "DELETE",
        "close_position_method": "POST",
        "modify_position_method": "PATCH",
        "price_method": "GET",
        "prices_method": "GET",
        "candles_method": "GET",
    }

    TOKEN_KEYS = [
        "access_token",
        "token",
        "id_token",
        "jwt",
        "sessionToken",
        "authToken",
        "data.access_token",
        "data.token",
        "data.jwt",
        "result.access_token",
        "result.token",
    ]

    def __init__(
        self,
        *,
        platform: str,
        account_id: str,
        password: str,
        server_name: str,
        api_base_url: str | None = None,
        **kwargs: Any,
    ):
        super().__init__()

        self.platform = platform.lower().strip()
        if self.platform not in self.DEFAULT_ENDPOINTS:
            raise ValueError(f"Unsupported platform for generic rest broker: {platform}")

        self.account_id = str(account_id or "").strip()
        self.password = str(password or "").strip()
        self.server_name = str(server_name or "").strip()
        if not self.account_id or not self.password or not self.server_name:
            raise ValueError("account_id, password and server_name are required")

        base_url = str(api_base_url or "").strip() or self.server_name
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"
        self.base_url = base_url.rstrip("/")

        self.timeout_seconds = max(5.0, _to_float(kwargs.get("request_timeout_seconds"), 20.0))
        self.auth_header_name = str(kwargs.get("auth_header_name") or "Authorization").strip() or "Authorization"
        self.auth_scheme = str(kwargs.get("auth_scheme") or "Bearer").strip() or "Bearer"
        self._token: str | None = str(kwargs.get("access_token") or "").strip() or None
        self._client: httpx.AsyncClient | None = None

        self.endpoints = dict(self.DEFAULT_ENDPOINTS[self.platform])
        for key in list(self.endpoints.keys()):
            override = kwargs.get(key)
            if override is not None and str(override).strip():
                self.endpoints[key] = str(override).strip()

        self.methods = dict(self.DEFAULT_METHODS)
        for key in list(self.DEFAULT_METHODS.keys()):
            override = kwargs.get(key)
            if override is not None and str(override).strip():
                self.methods[key] = str(override).strip().upper()

        self.extra_headers: dict[str, str] = {}
        extra_headers_raw = kwargs.get("extra_headers_json")
        if extra_headers_raw:
            try:
                parsed = json.loads(str(extra_headers_raw))
                if isinstance(parsed, dict):
                    self.extra_headers = {str(k): str(v) for k, v in parsed.items()}
            except Exception:
                self.extra_headers = {}

    @property
    def name(self) -> str:
        return self.platform.upper()

    @property
    def supported_markets(self) -> list[str]:
        return ["forex", "indices", "commodities", "stocks", "crypto"]

    def normalize_symbol(self, symbol: str) -> str:
        return (symbol or "").strip().upper().replace("/", "_")

    def denormalize_symbol(self, symbol: str) -> str:
        value = (symbol or "").strip().upper()
        if "_" in value:
            return value
        if len(value) == 6 and value[:3].isalpha() and value[3:].isalpha():
            return f"{value[:3]}_{value[3:]}"
        return value

    def _symbol_variants(self, symbol: str) -> dict[str, str]:
        normalized = self.normalize_symbol(symbol)
        return {
            "symbol": normalized,
            "symbol_underscore": normalized,
            "symbol_slash": normalized.replace("_", "/"),
            "symbol_compact": normalized.replace("_", ""),
        }

    def _build_basic_auth_header(self) -> str:
        raw = f"{self.account_id}:{self.password}".encode("utf-8")
        return f"Basic {base64.b64encode(raw).decode('utf-8')}"

    def _auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Account-Id": self.account_id,
            "X-Server-Name": self.server_name,
            **self.extra_headers,
        }
        if self._token:
            auth_value = f"{self.auth_scheme} {self._token}" if self.auth_scheme else self._token
            headers[self.auth_header_name] = auth_value
            if self.auth_header_name.lower() != "authorization":
                headers["Authorization"] = auth_value
        else:
            headers["Authorization"] = self._build_basic_auth_header()
        return headers

    def _endpoint(self, key: str) -> str:
        return str(self.endpoints.get(key) or "").strip()

    def _format_endpoint(self, template: str, **params: Any) -> str:
        value = template
        for key, raw in params.items():
            value = value.replace(f"{{{key}}}", quote_plus(str(raw)))
        return value

    def _build_url(self, endpoint: str) -> str:
        cleaned = endpoint.strip() or "/"
        return urljoin(f"{self.base_url}/", cleaned.lstrip("/"))

    async def _ensure_client(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout_seconds,
                verify=False,
            )

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        form_data: dict[str, Any] | None = None,
        retry_auth: bool = True,
    ) -> tuple[int, Any]:
        await self._ensure_client()
        if not self._client:
            raise ConnectionError("HTTP client not initialized")

        headers = self._auth_headers()
        if form_data is not None and json_data is None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        response = await self._client.request(
            method=method.upper(),
            url=self._build_url(endpoint),
            headers=headers,
            params=params,
            json=json_data,
            data=form_data,
        )
        status_code = response.status_code
        try:
            payload = response.json() if response.content else {}
        except Exception:
            payload = {"raw": response.text} if response.text else {}

        if status_code in {401, 403} and retry_auth and self._token:
            self._token = None
            await self._login()
            return await self._request(
                method,
                endpoint,
                params=params,
                json_data=json_data,
                form_data=form_data,
                retry_auth=False,
            )

        if status_code >= 400:
            detail = payload if isinstance(payload, dict) else {"raw": str(payload)}
            raise Exception(f"{self.platform} API error ({status_code}): {detail}")

        return status_code, payload

    def _extract_list(self, payload: Any, keys: list[str]) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in keys:
                value = _nested_get(payload, key) if "." in key else payload.get(key)
                if isinstance(value, list):
                    return value
        return []

    def _extract_token(self, payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        for key in self.TOKEN_KEYS:
            value = _nested_get(payload, key) if "." in key else payload.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    def _parse_order(self, payload: Any, fallback: dict[str, Any] | None = None) -> OrderResult:
        fallback = fallback or {}
        source = payload if isinstance(payload, dict) else {}
        status = _coerce_order_status(
            str(
                _pick(source, ["status", "state", "executionStatus", "result.status"], fallback.get("status", "pending"))
            )
        )
        side = _coerce_order_side(str(_pick(source, ["side", "direction"], fallback.get("side", "buy"))))
        order_type = _coerce_order_type(str(_pick(source, ["type", "orderType"], fallback.get("order_type", "market"))))
        size = _to_decimal(_pick(source, ["size", "qty", "quantity", "volume"], fallback.get("size", "0")), "0")
        filled_size = _to_decimal(
            _pick(source, ["filledSize", "filled_qty", "filledQuantity", "executedQty"], None),
            str(size),
        )
        if status != OrderStatus.FILLED and filled_size > size:
            filled_size = size

        order_id = str(_pick(source, ["orderId", "id", "dealId", "ticket"], fallback.get("order_id", "")) or "")
        symbol = self.denormalize_symbol(
            str(_pick(source, ["symbol", "instrument", "asset", "ticker"], fallback.get("symbol", "")) or "")
        )
        return OrderResult(
            order_id=order_id,
            client_order_id=_pick(source, ["clientOrderId", "client_order_id"], fallback.get("client_order_id")),
            symbol=symbol,
            side=side,
            order_type=order_type,
            status=status,
            size=size,
            filled_size=filled_size,
            price=(
                _to_decimal(_pick(source, ["price", "limitPrice", "orderPrice"], None))
                if _pick(source, ["price", "limitPrice", "orderPrice"], None) is not None
                else None
            ),
            average_fill_price=(
                _to_decimal(_pick(source, ["avgPrice", "averageFillPrice", "fillPrice"], None))
                if _pick(source, ["avgPrice", "averageFillPrice", "fillPrice"], None) is not None
                else None
            ),
            commission=_to_decimal(_pick(source, ["commission", "fees"], 0), "0"),
            created_at=_parse_timestamp(_pick(source, ["createdAt", "createTime", "timestamp"], datetime.now(UTC).isoformat())),
            filled_at=(
                _parse_timestamp(_pick(source, ["filledAt", "executedAt"], None))
                if _pick(source, ["filledAt", "executedAt"], None) is not None
                else None
            ),
            error_message=(
                str(_pick(source, ["error", "message", "reason"], "") or "")
                if status == OrderStatus.REJECTED
                else None
            ),
        )

    def _parse_position(self, payload: dict[str, Any]) -> Position:
        side = _coerce_side(str(_pick(payload, ["side", "direction", "positionSide"], "buy")))
        size = abs(_to_decimal(_pick(payload, ["size", "qty", "quantity", "volume", "lots"], 0), "0"))
        entry_price = _to_decimal(_pick(payload, ["entryPrice", "openPrice", "avgPrice", "price"], 0), "0")
        current_price = _to_decimal(_pick(payload, ["currentPrice", "marketPrice", "lastPrice"], 0), "0")
        bid = _to_decimal(_pick(payload, ["bid", "bestBid"], 0), "0")
        ask = _to_decimal(_pick(payload, ["ask", "bestAsk"], 0), "0")
        if current_price <= 0:
            current_price = ask if side == PositionSide.LONG else bid
        if current_price <= 0:
            current_price = entry_price
        return Position(
            position_id=str(_pick(payload, ["positionId", "id", "dealId", "ticket"], "")),
            symbol=self.denormalize_symbol(str(_pick(payload, ["symbol", "instrument", "asset", "ticker"], ""))),
            side=side,
            size=size,
            entry_price=entry_price,
            current_price=current_price,
            unrealized_pnl=_to_decimal(_pick(payload, ["unrealizedPnl", "floatingPnl", "profit", "pnl"], 0), "0"),
            margin_used=abs(_to_decimal(_pick(payload, ["marginUsed", "usedMargin", "margin"], 0), "0")),
            leverage=max(1, _to_int(_pick(payload, ["leverage"], 1), 1)),
            stop_loss=(
                _to_decimal(_pick(payload, ["stopLoss", "sl"], None))
                if _pick(payload, ["stopLoss", "sl"], None) is not None
                else None
            ),
            take_profit=(
                _to_decimal(_pick(payload, ["takeProfit", "tp"], None))
                if _pick(payload, ["takeProfit", "tp"], None) is not None
                else None
            ),
            opened_at=_parse_timestamp(_pick(payload, ["openTime", "openedAt", "createdAt"], datetime.now(UTC).isoformat())),
        )

    async def _login(self) -> bool:
        endpoint = self._endpoint("login_endpoint")
        if not endpoint:
            return False

        await self._ensure_client()
        if not self._client:
            raise ConnectionError("HTTP client not initialized")

        method = self.methods.get("login_method", "POST")
        url = self._build_url(endpoint)
        login_payload = {
            "accountId": self.account_id,
            "account_id": self.account_id,
            "login": self.account_id,
            "username": self.account_id,
            "password": self.password,
            "server": self.server_name,
            "serverName": self.server_name,
        }
        login_form = {
            "grant_type": "password",
            "username": self.account_id,
            "password": self.password,
            "server": self.server_name,
        }

        response = await self._client.request(
            method=method,
            url=url,
            headers=self._auth_headers(),
            json=login_payload,
        )
        if response.status_code in {404, 405}:
            form_headers = self._auth_headers()
            form_headers["Content-Type"] = "application/x-www-form-urlencoded"
            response = await self._client.request(
                method=method,
                url=url,
                headers=form_headers,
                data=login_form,
            )
        if response.status_code in {404, 405}:
            return False
        if response.status_code in {401, 403}:
            raise ConnectionError(f"{self.platform} credentials rejected ({response.status_code})")
        if response.status_code >= 500:
            raise ConnectionError(f"{self.platform} login server error ({response.status_code})")
        if response.status_code >= 400:
            raise ConnectionError(f"{self.platform} login failed ({response.status_code}): {response.text}")

        try:
            payload = response.json() if response.content else {}
        except Exception:
            payload = {}

        token = self._extract_token(payload)
        if token:
            self._token = token
        return True

    async def connect(self) -> None:
        if self._connected:
            return

        await self._ensure_client()
        if not self._client:
            raise ConnectionError("HTTP client not initialized")

        health_endpoint = self._endpoint("health_endpoint")
        if health_endpoint:
            response = await self._client.get(self._build_url(health_endpoint), headers=self._auth_headers())
            if response.status_code >= 500:
                raise ConnectionError(f"{self.platform} health endpoint error ({response.status_code})")

        await self._login()
        self._connected = True

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._token = None
        self._connected = False

    async def get_account_info(self) -> AccountInfo:
        endpoint = self._endpoint("account_endpoint")
        if not endpoint:
            return AccountInfo(
                account_id=self.account_id,
                balance=Decimal("0"),
                equity=Decimal("0"),
                margin_used=Decimal("0"),
                margin_available=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                realized_pnl_today=Decimal("0"),
                currency="USD",
                leverage=1,
                updated_at=datetime.now(UTC),
            )

        _, payload = await self._request(self.methods["account_method"], endpoint)
        source = payload
        if isinstance(source, list):
            source = source[0] if source else {}
        if not isinstance(source, dict):
            source = {}

        balance = _to_decimal(_pick(source, ["balance", "cash", "accountBalance", "summary.balance"], 0), "0")
        equity = _to_decimal(_pick(source, ["equity", "netAssetValue", "summary.equity"], None), str(balance))
        margin_used = _to_decimal(_pick(source, ["marginUsed", "usedMargin", "margin", "summary.marginUsed"], 0), "0")
        margin_available = _to_decimal(
            _pick(source, ["marginAvailable", "freeMargin", "availableMargin", "summary.marginAvailable"], None),
            "0",
        )
        if margin_available == 0 and equity > margin_used:
            margin_available = equity - margin_used

        return AccountInfo(
            account_id=str(_pick(source, ["accountId", "id", "login"], self.account_id)),
            balance=balance,
            equity=equity,
            margin_used=margin_used,
            margin_available=margin_available,
            unrealized_pnl=_to_decimal(_pick(source, ["unrealizedPnl", "floatingPnl", "pnl"], 0), "0"),
            realized_pnl_today=_to_decimal(_pick(source, ["realizedPnlToday", "todayPnl"], 0), "0"),
            currency=str(_pick(source, ["currency", "accountCurrency"], "USD") or "USD"),
            leverage=max(1, _to_int(_pick(source, ["leverage"], 1), 1)),
            updated_at=datetime.now(UTC),
        )

    async def get_instruments(self) -> list[Instrument]:
        endpoint = self._endpoint("symbols_endpoint")
        if not endpoint:
            return []
        _, payload = await self._request(self.methods["symbols_method"], endpoint)
        rows = self._extract_list(payload, ["symbols", "instruments", "items", "data", "result"])
        instruments: list[Instrument] = []
        for item in rows:
            if isinstance(item, str):
                symbol = self.normalize_symbol(item)
                instruments.append(
                    Instrument(
                        symbol=symbol,
                        name=symbol,
                        instrument_type="forex",
                    )
                )
                continue

            if not isinstance(item, dict):
                continue
            symbol = self.normalize_symbol(str(_pick(item, ["symbol", "name", "code", "instrument"], "") or ""))
            if not symbol:
                continue
            inst_type = str(_pick(item, ["type", "assetClass", "instrumentType"], "forex") or "forex").lower()
            instruments.append(
                Instrument(
                    symbol=symbol,
                    name=str(_pick(item, ["description", "name"], symbol) or symbol),
                    instrument_type=inst_type,
                    base_currency=_pick(item, ["baseCurrency"], None),
                    quote_currency=_pick(item, ["quoteCurrency"], None),
                    pip_location=_to_int(_pick(item, ["pipLocation", "digits"], -4), -4),
                    min_size=_to_decimal(_pick(item, ["minSize", "volumeMin"], 1), "1"),
                    max_size=(
                        _to_decimal(_pick(item, ["maxSize", "volumeMax"], 0), "0")
                        if _pick(item, ["maxSize", "volumeMax"], None) is not None
                        else None
                    ),
                    size_increment=_to_decimal(_pick(item, ["sizeStep", "volumeStep"], 1), "1"),
                    margin_rate=_to_decimal(_pick(item, ["marginRate"], 0.05), "0.05"),
                    trading_hours=_pick(item, ["tradingHours"], None),
                )
            )
        return instruments

    async def place_order(self, order: OrderRequest) -> OrderResult:
        endpoint = self._endpoint("place_order_endpoint")
        if not endpoint:
            return OrderResult(
                order_id="",
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                status=OrderStatus.REJECTED,
                size=order.size,
                filled_size=Decimal("0"),
                error_message=f"{self.platform} place_order endpoint not configured",
            )

        symbol = self.normalize_symbol(order.symbol)
        payload: dict[str, Any] = {
            "accountId": self.account_id,
            "server": self.server_name,
            "symbol": symbol,
            "side": "BUY" if order.side == OrderSide.BUY else "SELL",
            "direction": "buy" if order.side == OrderSide.BUY else "sell",
            "type": {
                OrderType.MARKET: "market",
                OrderType.LIMIT: "limit",
                OrderType.STOP: "stop",
                OrderType.STOP_LIMIT: "stop_limit",
            }.get(order.order_type, "market"),
            "orderType": {
                OrderType.MARKET: "MARKET",
                OrderType.LIMIT: "LIMIT",
                OrderType.STOP: "STOP",
                OrderType.STOP_LIMIT: "STOP_LIMIT",
            }.get(order.order_type, "MARKET"),
            "size": float(order.size),
            "qty": float(order.size),
            "quantity": float(order.size),
            "volume": float(order.size),
            "timeInForce": {
                TimeInForce.GTC: "GTC",
                TimeInForce.IOC: "IOC",
                TimeInForce.FOK: "FOK",
                TimeInForce.DAY: "DAY",
            }.get(order.time_in_force, "GTC"),
        }

        if order.order_type in {OrderType.LIMIT, OrderType.STOP_LIMIT} and order.price is not None:
            payload["price"] = float(order.price)
            payload["limitPrice"] = float(order.price)
        if order.order_type in {OrderType.STOP, OrderType.STOP_LIMIT} and order.stop_price is not None:
            payload["stopPrice"] = float(order.stop_price)
        if order.stop_loss is not None:
            payload["stopLoss"] = float(order.stop_loss)
            payload["sl"] = float(order.stop_loss)
        if order.take_profit is not None:
            payload["takeProfit"] = float(order.take_profit)
            payload["tp"] = float(order.take_profit)
        if order.client_order_id:
            payload["clientOrderId"] = order.client_order_id

        try:
            _, result = await self._request(
                self.methods["place_order_method"],
                endpoint,
                json_data=payload,
            )
            parsed = self._parse_order(
                result,
                fallback={
                    "symbol": symbol,
                    "side": order.side.value,
                    "order_type": order.order_type.value,
                    "size": str(order.size),
                    "client_order_id": order.client_order_id,
                },
            )
            if not parsed.order_id:
                parsed.order_id = f"{self.platform}-order-{int(datetime.now(UTC).timestamp())}"
            return parsed
        except Exception as exc:
            return OrderResult(
                order_id="",
                client_order_id=order.client_order_id,
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                status=OrderStatus.REJECTED,
                size=order.size,
                filled_size=Decimal("0"),
                error_message=str(exc),
            )

    async def cancel_order(self, order_id: str) -> bool:
        template = self._endpoint("cancel_order_endpoint_template")
        endpoint = self._format_endpoint(template, order_id=order_id) if template else self._endpoint("orders_endpoint")
        if not endpoint:
            return False
        try:
            await self._request(
                self.methods["cancel_order_method"],
                endpoint,
                json_data={"orderId": order_id},
            )
            return True
        except Exception:
            return False

    async def get_order(self, order_id: str) -> OrderResult | None:
        template = self._endpoint("order_endpoint_template")
        if template:
            endpoint = self._format_endpoint(template, order_id=order_id)
            try:
                _, payload = await self._request(self.methods["order_method"], endpoint)
                order = self._parse_order(payload, fallback={"order_id": order_id})
                if not order.order_id:
                    order.order_id = order_id
                return order
            except Exception:
                return None

        for order in await self.get_open_orders():
            if order.order_id == order_id:
                return order
        return None

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        endpoint = self._endpoint("orders_endpoint")
        if not endpoint:
            return []
        params: dict[str, Any] | None = None
        if symbol:
            params = {"symbol": self.normalize_symbol(symbol)}
        _, payload = await self._request(self.methods["orders_method"], endpoint, params=params)
        rows = self._extract_list(payload, ["orders", "items", "data", "result"])
        parsed: list[OrderResult] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            order = self._parse_order(item)
            if symbol and self.normalize_symbol(order.symbol) != self.normalize_symbol(symbol):
                continue
            parsed.append(order)
        return parsed

    async def get_positions(self) -> list[Position]:
        endpoint = self._endpoint("positions_endpoint")
        if not endpoint:
            return []
        _, payload = await self._request(self.methods["positions_method"], endpoint)
        rows = self._extract_list(payload, ["positions", "openPositions", "items", "data", "result"])
        positions: list[Position] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            position = self._parse_position(item)
            if position.size <= 0:
                continue
            positions.append(position)
        return positions

    async def get_position(self, symbol: str) -> Position | None:
        target = self.normalize_symbol(symbol)
        for position in await self.get_positions():
            if self.normalize_symbol(position.symbol) == target:
                return position
        return None

    async def close_position(
        self,
        symbol: str,
        size: Decimal | None = None,
    ) -> OrderResult:
        position = await self.get_position(symbol)
        if not position:
            return OrderResult(
                order_id="",
                symbol=symbol,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                status=OrderStatus.REJECTED,
                size=size or Decimal("0"),
                filled_size=Decimal("0"),
                error_message=f"No open position found for {symbol}",
            )

        close_size = size or position.size
        payload = {
            "accountId": self.account_id,
            "server": self.server_name,
            "symbol": self.normalize_symbol(position.symbol),
            "positionId": position.position_id,
            "size": float(close_size),
            "qty": float(close_size),
            "volume": float(close_size),
        }
        side = OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY
        payload["side"] = "SELL" if side == OrderSide.SELL else "BUY"

        template = self._endpoint("close_position_endpoint_template")
        endpoint = ""
        if template and "{position_id}" in template:
            endpoint = self._format_endpoint(template, position_id=position.position_id)
        elif self._endpoint("close_position_by_symbol_endpoint"):
            endpoint = self._endpoint("close_position_by_symbol_endpoint")
        elif template:
            endpoint = template

        if not endpoint:
            return OrderResult(
                order_id="",
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                status=OrderStatus.REJECTED,
                size=close_size,
                filled_size=Decimal("0"),
                error_message=f"{self.platform} close_position endpoint not configured",
            )

        try:
            _, result = await self._request(
                self.methods["close_position_method"],
                endpoint,
                json_data=payload,
            )
            parsed = self._parse_order(
                result,
                fallback={
                    "symbol": self.normalize_symbol(position.symbol),
                    "side": side.value,
                    "order_type": OrderType.MARKET.value,
                    "size": str(close_size),
                },
            )
            if not parsed.order_id:
                parsed.order_id = f"{self.platform}-close-{int(datetime.now(UTC).timestamp())}"
            return parsed
        except Exception as exc:
            return OrderResult(
                order_id="",
                symbol=position.symbol,
                side=side,
                order_type=OrderType.MARKET,
                status=OrderStatus.REJECTED,
                size=close_size,
                filled_size=Decimal("0"),
                error_message=str(exc),
            )

    async def modify_position(
        self,
        symbol: str,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
    ) -> bool:
        if stop_loss is None and take_profit is None:
            return True
        position = await self.get_position(symbol)
        if not position:
            return False

        payload: dict[str, Any] = {
            "accountId": self.account_id,
            "server": self.server_name,
            "symbol": self.normalize_symbol(position.symbol),
            "positionId": position.position_id,
        }
        if stop_loss is not None:
            payload["stopLoss"] = float(stop_loss)
            payload["sl"] = float(stop_loss)
        if take_profit is not None:
            payload["takeProfit"] = float(take_profit)
            payload["tp"] = float(take_profit)

        template = self._endpoint("modify_position_endpoint_template")
        endpoint = self._format_endpoint(template, position_id=position.position_id) if template else ""
        if not endpoint:
            endpoint = self._endpoint("close_position_by_symbol_endpoint")
        if not endpoint:
            return False

        try:
            await self._request(
                self.methods["modify_position_method"],
                endpoint,
                json_data=payload,
            )
            return True
        except Exception:
            return False

    def _parse_tick(self, payload: Any, symbol: str) -> Tick:
        source = payload
        if isinstance(source, list):
            source = source[0] if source else {}
        if not isinstance(source, dict):
            source = {}

        quote_symbol = str(_pick(source, ["symbol", "instrument", "asset", "ticker"], symbol) or symbol)
        bid = _to_decimal(_pick(source, ["bid", "bestBid", "bidPrice"], None), "0")
        ask = _to_decimal(_pick(source, ["ask", "bestAsk", "askPrice"], None), "0")
        if bid <= 0 or ask <= 0:
            mid = _to_decimal(_pick(source, ["mid", "price", "last", "lastPrice", "close"], 0), "0")
            if mid > 0:
                if bid <= 0:
                    bid = mid
                if ask <= 0:
                    ask = mid
        if bid <= 0 or ask <= 0:
            raise ValueError(f"Invalid quote payload for {symbol}: {source}")
        return Tick(
            symbol=self.denormalize_symbol(quote_symbol),
            bid=bid,
            ask=ask,
            timestamp=_parse_timestamp(_pick(source, ["timestamp", "time", "updatedAt"], datetime.now(UTC).isoformat())),
        )

    async def get_current_price(self, symbol: str) -> Tick:
        normalized = self.normalize_symbol(symbol)
        variants = self._symbol_variants(normalized)

        template = self._endpoint("price_endpoint_template")
        if template:
            trial_order = ["symbol", "symbol_compact", "symbol_slash", "symbol_underscore"]
            last_error: Exception | None = None
            for key in trial_order:
                endpoint = self._format_endpoint(
                    template,
                    symbol=variants["symbol"],
                    symbol_compact=variants["symbol_compact"],
                    symbol_slash=variants["symbol_slash"],
                    symbol_underscore=variants["symbol_underscore"],
                )
                endpoint = endpoint.replace(quote_plus(variants["symbol"]), quote_plus(variants[key]))
                try:
                    _, payload = await self._request(self.methods["price_method"], endpoint)
                    return self._parse_tick(payload, normalized)
                except Exception as exc:
                    last_error = exc
            if last_error:
                raise last_error

        prices_endpoint = self._endpoint("prices_endpoint")
        if not prices_endpoint:
            raise ValueError(f"{self.platform} price endpoints not configured")
        _, payload = await self._request(
            self.methods["prices_method"],
            prices_endpoint,
            params={"symbol": normalized, "symbols": normalized},
        )

        if isinstance(payload, dict):
            for key in ("quotes", "prices", "ticks", "data", "result"):
                value = payload.get(key)
                if isinstance(value, dict):
                    for candidate in (
                        variants["symbol"],
                        variants["symbol_compact"],
                        variants["symbol_slash"],
                        variants["symbol_underscore"],
                    ):
                        if candidate in value:
                            return self._parse_tick(value[candidate], normalized)
                        for nested_key, nested_val in value.items():
                            if str(nested_key).upper() == candidate.upper():
                                return self._parse_tick(nested_val, normalized)
                if isinstance(value, list):
                    for item in value:
                        if not isinstance(item, dict):
                            continue
                        raw_symbol = str(_pick(item, ["symbol", "instrument", "asset", "ticker"], "") or "")
                        if self.normalize_symbol(raw_symbol) == variants["symbol"]:
                            return self._parse_tick(item, normalized)

        return self._parse_tick(payload, normalized)

    async def get_prices(self, symbols: list[str]) -> dict[str, Tick]:
        prices: dict[str, Tick] = {}
        for symbol in symbols:
            try:
                prices[symbol] = await self.get_current_price(symbol)
            except Exception:
                continue
        return prices

    async def stream_prices(self, symbols: list[str]) -> AsyncIterator[Tick]:
        while self._connected:
            prices = await self.get_prices(symbols)
            for tick in prices.values():
                yield tick
            await asyncio.sleep(1)

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        count: int = 100,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> list[Candle]:
        endpoint_template = self._endpoint("candles_endpoint_template")
        if not endpoint_template:
            return []

        variants = self._symbol_variants(symbol)
        endpoint = self._format_endpoint(
            endpoint_template,
            symbol=variants["symbol"],
            symbol_compact=variants["symbol_compact"],
            symbol_slash=variants["symbol_slash"],
            symbol_underscore=variants["symbol_underscore"],
        )
        params: dict[str, Any] = {
            "timeframe": timeframe,
            "granularity": timeframe,
            "count": max(1, min(int(count or 100), 2000)),
            "limit": max(1, min(int(count or 100), 2000)),
        }
        if from_time:
            params["from"] = from_time.astimezone(UTC).isoformat()
        if to_time:
            params["to"] = to_time.astimezone(UTC).isoformat()

        _, payload = await self._request(
            self.methods["candles_method"],
            endpoint,
            params=params,
        )
        rows = self._extract_list(payload, ["candles", "bars", "items", "data", "result"])
        candles: list[Candle] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            candles.append(
                Candle(
                    symbol=self.denormalize_symbol(str(_pick(row, ["symbol"], variants["symbol"]) or variants["symbol"])),
                    timestamp=_parse_timestamp(_pick(row, ["timestamp", "time", "t"], datetime.now(UTC).isoformat())),
                    open=_to_decimal(_pick(row, ["open", "o"], 0), "0"),
                    high=_to_decimal(_pick(row, ["high", "h"], 0), "0"),
                    low=_to_decimal(_pick(row, ["low", "l"], 0), "0"),
                    close=_to_decimal(_pick(row, ["close", "c"], 0), "0"),
                    volume=_to_decimal(_pick(row, ["volume", "v"], 0), "0"),
                    timeframe=timeframe,
                )
            )
        return candles


class CTraderBroker(PlatformRestBroker):
    """Concrete generic adapter configured for cTrader-like endpoints."""

    def __init__(
        self,
        *,
        account_id: str,
        password: str,
        server_name: str,
        api_base_url: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            platform="ctrader",
            account_id=account_id,
            password=password,
            server_name=server_name,
            api_base_url=api_base_url,
            **kwargs,
        )


class DXTradeBroker(PlatformRestBroker):
    """Concrete generic adapter configured for DXtrade-like endpoints."""

    def __init__(
        self,
        *,
        account_id: str,
        password: str,
        server_name: str,
        api_base_url: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            platform="dxtrade",
            account_id=account_id,
            password=password,
            server_name=server_name,
            api_base_url=api_base_url,
            **kwargs,
        )


class MatchTraderBroker(PlatformRestBroker):
    """Concrete generic adapter configured for Match-Trader-like endpoints."""

    def __init__(
        self,
        *,
        account_id: str,
        password: str,
        server_name: str,
        api_base_url: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            platform="matchtrader",
            account_id=account_id,
            password=password,
            server_name=server_name,
            api_base_url=api_base_url,
            **kwargs,
        )
