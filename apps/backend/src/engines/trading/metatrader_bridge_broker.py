"""
MetaTrader Bridge Broker

Implements BaseBroker against a proprietary MT4/MT5 bridge service.
The bridge runs on Windows nodes and owns terminal sessions.
"""

import asyncio
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
    for candidate in (text.replace("Z", "+00:00"), text.replace("/", "-")):
        try:
            return datetime.fromisoformat(candidate)
        except Exception:
            continue
    return datetime.now(UTC)


def _nested_get(payload: Any, path: str) -> Any:
    if not path or not isinstance(payload, dict):
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
        value = _nested_get(payload, key) if "." in key else payload.get(key)
        if value is not None:
            return value
    return default


def _normalize_server_candidates(raw: Any) -> list[str]:
    if raw is None:
        return []

    values: list[str] = []
    if isinstance(raw, (list, tuple, set)):
        values = [str(item or "").strip() for item in raw]
    else:
        text = str(raw or "").replace(";", ",").replace("\n", ",").replace("|", ",")
        values = [part.strip() for part in text.split(",")]

    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


class MetaTraderBridgeBroker(BaseBroker):
    """
    MT4/MT5 broker implementation through a bridge gateway.

    Expected bridge contract (customizable with endpoint templates):
    - POST connect endpoint -> returns session id
    - REST endpoints scoped by {session_id}
    """

    DEFAULT_TIMEOUT_SECONDS = 90.0

    def __init__(
        self,
        *,
        account_number: str,
        password: str,
        bridge_base_url: str,
        server_name: str | None = None,
        server_candidates: list[str] | str | None = None,
        platform: str = "mt5",
        bridge_api_key: str | None = None,
        terminal_path: str | None = None,
        data_path: str | None = None,
        workspace_id: str | None = None,
        connect_endpoint: str = "/api/v1/sessions/connect",
        disconnect_endpoint: str = "/api/v1/sessions/{session_id}/disconnect",
        account_endpoint: str = "/api/v1/sessions/{session_id}/account",
        positions_endpoint: str = "/api/v1/sessions/{session_id}/positions",
        price_endpoint: str = "/api/v1/sessions/{session_id}/prices/{symbol}",
        prices_endpoint: str = "/api/v1/sessions/{session_id}/prices",
        candles_endpoint: str = "/api/v1/sessions/{session_id}/candles/{symbol}",
        place_order_endpoint: str = "/api/v1/sessions/{session_id}/orders",
        open_orders_endpoint: str = "/api/v1/sessions/{session_id}/orders/open",
        order_endpoint: str = "/api/v1/sessions/{session_id}/orders/{order_id}",
        cancel_order_endpoint: str = "/api/v1/sessions/{session_id}/orders/{order_id}",
        close_position_endpoint: str = "/api/v1/sessions/{session_id}/positions/close",
        modify_position_endpoint: str = "/api/v1/sessions/{session_id}/positions/modify",
        **kwargs: Any,
    ):
        super().__init__()

        self.account_number = str(account_number or "").strip()
        self.password = str(password or "").strip()
        self.server_name = str(server_name or "").strip()
        self.server_candidates = _normalize_server_candidates(server_candidates)
        self.platform = str(platform or "mt5").strip().lower()
        if self.platform not in {"mt4", "mt5"}:
            self.platform = "mt5"
        if not self.account_number or not self.password:
            raise ValueError("account_number and password are required for MT bridge")
        if self.platform == "mt4" and not self.server_name:
            raise ValueError("server_name is required for MT4 bridge mode")

        raw_url = str(bridge_base_url or "").strip()
        if not raw_url:
            raise ValueError("bridge_base_url is required for MT bridge")
        if not raw_url.startswith(("http://", "https://")):
            raw_url = f"http://{raw_url}"
        self.base_url = raw_url.rstrip("/")
        self.bridge_api_key = (bridge_api_key or "").strip() or None
        self.timeout_seconds = max(float(kwargs.get("timeout_seconds", self.DEFAULT_TIMEOUT_SECONDS)), 5.0)
        self.terminal_path = str(terminal_path or "").strip() or None
        self.data_path = str(data_path or "").strip() or None
        self.workspace_id = str(workspace_id or "").strip() or None

        self.connect_endpoint = connect_endpoint
        self.disconnect_endpoint = disconnect_endpoint
        self.account_endpoint = account_endpoint
        self.positions_endpoint = positions_endpoint
        self.price_endpoint = price_endpoint
        self.prices_endpoint = prices_endpoint
        self.candles_endpoint = candles_endpoint
        self.place_order_endpoint = place_order_endpoint
        self.open_orders_endpoint = open_orders_endpoint
        self.order_endpoint = order_endpoint
        self.cancel_order_endpoint = cancel_order_endpoint
        self.close_position_endpoint = close_position_endpoint
        self.modify_position_endpoint = modify_position_endpoint

        self._session_id: str | None = None
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return f"MT-BRIDGE-{self.platform.upper()}"

    @property
    def supported_markets(self) -> list[str]:
        return ["forex", "indices", "commodities", "stocks", "crypto"]

    def normalize_symbol(self, symbol: str) -> str:
        return (symbol or "").strip().upper().replace("/", "").replace("_", "")

    def denormalize_symbol(self, symbol: str) -> str:
        value = (symbol or "").strip().upper().replace("/", "").replace("_", "")
        if len(value) == 6 and value[:3].isalpha() and value[3:].isalpha():
            return f"{value[:3]}_{value[3:]}"
        return value

    async def _ensure_client(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout_seconds,
                verify=False,
            )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.bridge_api_key:
            headers["Authorization"] = f"Bearer {self.bridge_api_key}"
            headers["X-Bridge-Key"] = self.bridge_api_key
        return headers

    def _build_url(self, endpoint: str) -> str:
        return urljoin(f"{self.base_url}/", endpoint.lstrip("/"))

    def _fmt_endpoint(self, template: str, **params: Any) -> str:
        value = template
        for key, raw in params.items():
            value = value.replace(f"{{{key}}}", quote_plus(str(raw)))
        return value

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
            raise ConnectionError("Bridge HTTP client not initialized")

        response = await self._client.request(
            method=method.upper(),
            url=self._build_url(endpoint),
            headers=self._headers(),
            params=params,
            json=data,
        )
        if response.status_code >= 400:
            detail = response.text[:400]
            raise Exception(f"MT bridge error ({response.status_code}): {detail}")
        if not response.content:
            return {}
        try:
            return response.json()
        except Exception:
            return {"raw": response.text}

    def _require_session(self) -> str:
        if not self._session_id:
            raise ConnectionError("MT bridge session not established")
        return self._session_id

    async def connect(self) -> None:
        if self._connected:
            return

        payload: dict[str, Any] = {
            "platform": self.platform,
            "login": self.account_number,
            "account_number": self.account_number,
            "password": self.password,
        }
        if self.server_name:
            payload["server"] = self.server_name
            payload["server_name"] = self.server_name
        if self.server_candidates:
            payload["server_candidates"] = list(self.server_candidates)
        if self.terminal_path:
            payload["terminal_path"] = self.terminal_path
        if self.data_path:
            payload["data_path"] = self.data_path
        if self.workspace_id:
            payload["workspace_id"] = self.workspace_id

        response = await self._request("POST", self.connect_endpoint, data=payload)
        session_id = str(
            _pick(
                response,
                [
                    "session_id",
                    "sessionId",
                    "data.session_id",
                    "data.sessionId",
                    "result.session_id",
                    "result.sessionId",
                ],
                "",
            )
            or ""
        ).strip()
        if not session_id:
            raise ConnectionError("MT bridge connect response missing session_id")
        resolved_server = str(
            _pick(
                response,
                [
                    "server",
                    "server_name",
                    "data.server",
                    "data.server_name",
                    "result.server",
                    "result.server_name",
                ],
                "",
            )
            or ""
        ).strip()
        if resolved_server:
            self.server_name = resolved_server
        self._session_id = session_id
        self._connected = True

    async def disconnect(self) -> None:
        if self._client and self._session_id:
            try:
                endpoint = self._fmt_endpoint(self.disconnect_endpoint, session_id=self._session_id)
                await self._request("POST", endpoint, data={"session_id": self._session_id})
            except Exception:
                pass
        if self._client:
            await self._client.aclose()
            self._client = None
        self._session_id = None
        self._connected = False

    async def get_account_info(self) -> AccountInfo:
        endpoint = self._fmt_endpoint(self.account_endpoint, session_id=self._require_session())
        payload = await self._request("GET", endpoint)
        source = payload[0] if isinstance(payload, list) and payload else payload
        if not isinstance(source, dict):
            source = {}

        balance = _to_decimal(_pick(source, ["balance", "account.balance", "data.balance"], 0), "0")
        equity = _to_decimal(_pick(source, ["equity", "account.equity", "data.equity"], None), str(balance))
        margin_used = _to_decimal(_pick(source, ["margin", "margin_used", "account.margin"], 0), "0")
        free_margin = _to_decimal(_pick(source, ["freeMargin", "free_margin", "account.freeMargin"], None), "0")
        if free_margin == 0 and equity > margin_used:
            free_margin = equity - margin_used

        return AccountInfo(
            account_id=str(_pick(source, ["accountId", "login", "account_id"], self.account_number)),
            balance=balance,
            equity=equity,
            margin_used=margin_used,
            margin_available=free_margin,
            unrealized_pnl=_to_decimal(_pick(source, ["profit", "floatingProfit", "unrealized_pnl"], 0), "0"),
            realized_pnl_today=_to_decimal(_pick(source, ["realized_pnl_today", "todayProfit"], 0), "0"),
            currency=str(_pick(source, ["currency", "accountCurrency"], "USD") or "USD"),
            leverage=max(1, _to_int(_pick(source, ["leverage"], 1), 1)),
            updated_at=datetime.now(UTC),
        )

    async def get_instruments(self) -> list[Instrument]:
        # Optional endpoint can be added later. For now keep empty to avoid hard dependency.
        return []

    def _parse_order_status(self, value: str | None) -> OrderStatus:
        text = (value or "").lower()
        if text in {"filled", "executed", "done", "closed"}:
            return OrderStatus.FILLED
        if text in {"partial", "partially_filled"}:
            return OrderStatus.PARTIALLY_FILLED
        if text in {"cancelled", "canceled"}:
            return OrderStatus.CANCELLED
        if text in {"rejected", "error"}:
            return OrderStatus.REJECTED
        if text in {"expired"}:
            return OrderStatus.EXPIRED
        return OrderStatus.PENDING

    def _parse_order_type(self, value: str | None) -> OrderType:
        text = (value or "").lower()
        if text == "limit":
            return OrderType.LIMIT
        if text == "stop":
            return OrderType.STOP
        if text in {"stop_limit", "stoplimit"}:
            return OrderType.STOP_LIMIT
        return OrderType.MARKET

    async def place_order(self, order: OrderRequest) -> OrderResult:
        endpoint = self._fmt_endpoint(self.place_order_endpoint, session_id=self._require_session())
        payload: dict[str, Any] = {
            "symbol": self.normalize_symbol(order.symbol),
            "side": "buy" if order.side == OrderSide.BUY else "sell",
            "order_type": order.order_type.value,
            "volume": float(order.size),
            "time_in_force": order.time_in_force.value,
            "stop_loss": float(order.stop_loss) if order.stop_loss is not None else None,
            "take_profit": float(order.take_profit) if order.take_profit is not None else None,
            "price": float(order.price) if order.price is not None else None,
            "stop_price": float(order.stop_price) if order.stop_price is not None else None,
            "client_order_id": order.client_order_id,
        }
        result = await self._request("POST", endpoint, data=payload)
        status = self._parse_order_status(str(_pick(result, ["status", "state"], "pending")))
        return OrderResult(
            order_id=str(_pick(result, ["order_id", "orderId", "ticket"], "")),
            client_order_id=order.client_order_id,
            symbol=self.denormalize_symbol(str(_pick(result, ["symbol"], self.normalize_symbol(order.symbol)))),
            side=order.side,
            order_type=order.order_type,
            status=status,
            size=order.size,
            filled_size=order.size if status == OrderStatus.FILLED else Decimal("0"),
            average_fill_price=(
                _to_decimal(_pick(result, ["fill_price", "price"], None))
                if _pick(result, ["fill_price", "price"], None) is not None
                else None
            ),
            error_message=str(_pick(result, ["error", "message"], "")) if status == OrderStatus.REJECTED else None,
        )

    async def cancel_order(self, order_id: str) -> bool:
        endpoint = self._fmt_endpoint(self.cancel_order_endpoint, session_id=self._require_session(), order_id=order_id)
        try:
            await self._request("DELETE", endpoint)
            return True
        except Exception:
            return False

    async def get_order(self, order_id: str) -> OrderResult | None:
        endpoint = self._fmt_endpoint(self.order_endpoint, session_id=self._require_session(), order_id=order_id)
        try:
            payload = await self._request("GET", endpoint)
            status = self._parse_order_status(str(_pick(payload, ["status", "state"], "pending")))
            side_raw = str(_pick(payload, ["side"], "buy")).lower()
            side = OrderSide.SELL if side_raw == "sell" else OrderSide.BUY
            return OrderResult(
                order_id=str(_pick(payload, ["order_id", "orderId", "ticket"], order_id)),
                symbol=self.denormalize_symbol(str(_pick(payload, ["symbol"], ""))),
                side=side,
                order_type=self._parse_order_type(str(_pick(payload, ["order_type", "type"], "market"))),
                status=status,
                size=_to_decimal(_pick(payload, ["volume", "size"], 0), "0"),
                filled_size=_to_decimal(_pick(payload, ["filled_volume", "filled"], 0), "0"),
            )
        except Exception:
            return None

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        endpoint = self._fmt_endpoint(self.open_orders_endpoint, session_id=self._require_session())
        payload = await self._request("GET", endpoint)
        rows = payload if isinstance(payload, list) else _pick(payload, ["orders", "items", "data"], [])
        if not isinstance(rows, list):
            return []
        result: list[OrderResult] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            item_symbol = self.denormalize_symbol(str(_pick(item, ["symbol"], "")))
            if symbol and self.normalize_symbol(item_symbol) != self.normalize_symbol(symbol):
                continue
            side = OrderSide.SELL if str(_pick(item, ["side"], "buy")).lower() == "sell" else OrderSide.BUY
            status = self._parse_order_status(str(_pick(item, ["status", "state"], "pending")))
            result.append(
                OrderResult(
                    order_id=str(_pick(item, ["order_id", "orderId", "ticket"], "")),
                    symbol=item_symbol,
                    side=side,
                    order_type=self._parse_order_type(str(_pick(item, ["order_type", "type"], "market"))),
                    status=status,
                    size=_to_decimal(_pick(item, ["volume", "size"], 0), "0"),
                    filled_size=_to_decimal(_pick(item, ["filled_volume", "filled"], 0), "0"),
                )
            )
        return result

    async def get_positions(self) -> list[Position]:
        endpoint = self._fmt_endpoint(self.positions_endpoint, session_id=self._require_session())
        payload = await self._request("GET", endpoint)
        rows = payload if isinstance(payload, list) else _pick(payload, ["positions", "items", "data"], [])
        if not isinstance(rows, list):
            return []
        positions: list[Position] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            side_raw = str(_pick(item, ["side", "type"], "buy")).lower()
            side = PositionSide.SHORT if side_raw in {"sell", "short"} else PositionSide.LONG
            symbol = self.denormalize_symbol(str(_pick(item, ["symbol"], "")))
            positions.append(
                Position(
                    position_id=str(_pick(item, ["position_id", "positionId", "ticket"], "")),
                    symbol=symbol,
                    side=side,
                    size=abs(_to_decimal(_pick(item, ["volume", "size"], 0), "0")),
                    entry_price=_to_decimal(_pick(item, ["open_price", "entry_price"], 0), "0"),
                    current_price=_to_decimal(_pick(item, ["current_price", "price"], 0), "0"),
                    unrealized_pnl=_to_decimal(_pick(item, ["profit", "pnl"], 0), "0"),
                    margin_used=abs(_to_decimal(_pick(item, ["margin"], 0), "0")),
                    leverage=max(1, _to_int(_pick(item, ["leverage"], 1), 1)),
                    stop_loss=(
                        _to_decimal(_pick(item, ["stop_loss", "sl"], None))
                        if _pick(item, ["stop_loss", "sl"], None) is not None
                        else None
                    ),
                    take_profit=(
                        _to_decimal(_pick(item, ["take_profit", "tp"], None))
                        if _pick(item, ["take_profit", "tp"], None) is not None
                        else None
                    ),
                    opened_at=_parse_timestamp(_pick(item, ["opened_at", "open_time"], None)),
                )
            )
        return positions

    async def get_position(self, symbol: str) -> Position | None:
        target = self.normalize_symbol(symbol)
        for position in await self.get_positions():
            if self.normalize_symbol(position.symbol) == target:
                return position
        return None

    async def close_position(self, symbol: str, size: Decimal | None = None) -> OrderResult:
        endpoint = self._fmt_endpoint(self.close_position_endpoint, session_id=self._require_session())
        payload = {"symbol": self.normalize_symbol(symbol)}
        if size is not None:
            payload["volume"] = float(size)
        result = await self._request("POST", endpoint, data=payload)
        status = self._parse_order_status(str(_pick(result, ["status", "state"], "filled")))
        close_size = size or _to_decimal(_pick(result, ["volume", "size"], 0), "0")
        side_raw = str(_pick(result, ["side"], "sell")).lower()
        side = OrderSide.SELL if side_raw == "sell" else OrderSide.BUY
        return OrderResult(
            order_id=str(_pick(result, ["order_id", "orderId", "ticket"], "")),
            symbol=self.denormalize_symbol(str(_pick(result, ["symbol"], self.normalize_symbol(symbol)))),
            side=side,
            order_type=OrderType.MARKET,
            status=status,
            size=close_size,
            filled_size=close_size if status == OrderStatus.FILLED else Decimal("0"),
            average_fill_price=(
                _to_decimal(_pick(result, ["fill_price", "price"], None))
                if _pick(result, ["fill_price", "price"], None) is not None
                else None
            ),
            error_message=str(_pick(result, ["error", "message"], "")) if status == OrderStatus.REJECTED else None,
        )

    async def modify_position(
        self,
        symbol: str,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
    ) -> bool:
        if stop_loss is None and take_profit is None:
            return True
        endpoint = self._fmt_endpoint(self.modify_position_endpoint, session_id=self._require_session())
        payload: dict[str, Any] = {"symbol": self.normalize_symbol(symbol)}
        if stop_loss is not None:
            payload["stop_loss"] = float(stop_loss)
        if take_profit is not None:
            payload["take_profit"] = float(take_profit)
        try:
            await self._request("POST", endpoint, data=payload)
            return True
        except Exception:
            return False

    async def get_current_price(self, symbol: str) -> Tick:
        endpoint = self._fmt_endpoint(
            self.price_endpoint,
            session_id=self._require_session(),
            symbol=self.normalize_symbol(symbol),
        )
        payload = await self._request("GET", endpoint)
        bid = _to_decimal(_pick(payload, ["bid"], 0), "0")
        ask = _to_decimal(_pick(payload, ["ask"], 0), "0")
        if bid <= 0 or ask <= 0:
            mid = _to_decimal(_pick(payload, ["mid", "price", "last"], 0), "0")
            if mid > 0:
                bid = mid
                ask = mid
        if bid <= 0 or ask <= 0:
            raise ValueError(f"Invalid bridge price response for {symbol}: {payload}")
        return Tick(
            symbol=self.denormalize_symbol(str(_pick(payload, ["symbol"], self.normalize_symbol(symbol)))),
            bid=bid,
            ask=ask,
            timestamp=_parse_timestamp(_pick(payload, ["timestamp", "time"], None)),
        )

    async def get_prices(self, symbols: list[str]) -> dict[str, Tick]:
        result: dict[str, Tick] = {}
        # Bridge bulk endpoint can be added later; for now use safe per-symbol polling.
        for symbol in symbols:
            try:
                result[symbol] = await self.get_current_price(symbol)
            except Exception:
                continue
        return result

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
        endpoint = self._fmt_endpoint(
            self.candles_endpoint,
            session_id=self._require_session(),
            symbol=self.normalize_symbol(symbol),
        )
        params: dict[str, Any] = {"timeframe": timeframe, "count": max(1, min(int(count or 100), 2000))}
        if from_time:
            params["from"] = from_time.astimezone(UTC).isoformat()
        if to_time:
            params["to"] = to_time.astimezone(UTC).isoformat()
        payload = await self._request("GET", endpoint, params=params)
        rows = payload if isinstance(payload, list) else _pick(payload, ["candles", "bars", "items", "data"], [])
        if not isinstance(rows, list):
            return []

        candles: list[Candle] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            candles.append(
                Candle(
                    symbol=self.denormalize_symbol(str(_pick(row, ["symbol"], self.normalize_symbol(symbol)))),
                    timestamp=_parse_timestamp(_pick(row, ["timestamp", "time", "t"], None)),
                    open=_to_decimal(_pick(row, ["open", "o"], 0), "0"),
                    high=_to_decimal(_pick(row, ["high", "h"], 0), "0"),
                    low=_to_decimal(_pick(row, ["low", "l"], 0), "0"),
                    close=_to_decimal(_pick(row, ["close", "c"], 0), "0"),
                    volume=_to_decimal(_pick(row, ["volume", "v"], 0), "0"),
                    timeframe=timeframe,
                )
            )
        return candles
