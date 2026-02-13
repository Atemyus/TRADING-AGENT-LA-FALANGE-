"""
Alpaca Broker Implementation

Implements BaseBroker using Alpaca Trading API v2.
Supports stocks and crypto accounts (paper/live).
"""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from src.core.config import settings
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


def _parse_iso_timestamp(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        return datetime.now(UTC)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(UTC)


class AlpacaBroker(BaseBroker):
    """Alpaca broker implementation."""

    PAPER_API_URL = "https://paper-api.alpaca.markets"
    LIVE_API_URL = "https://api.alpaca.markets"
    DATA_API_URL = "https://data.alpaca.markets"

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        paper: bool = True,
    ):
        super().__init__()
        self.api_key = api_key or settings.ALPACA_API_KEY
        self.secret_key = secret_key or settings.ALPACA_SECRET_KEY
        self.paper = bool(paper)
        if not self.api_key:
            raise ValueError("Alpaca API key is required")
        if not self.secret_key:
            raise ValueError("Alpaca secret key is required")

        self.base_url = self.PAPER_API_URL if self.paper else self.LIVE_API_URL
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "Alpaca"

    @property
    def supported_markets(self) -> list[str]:
        return ["stocks", "crypto"]

    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json",
        }

    async def connect(self) -> None:
        if self._connected:
            return
        self._client = httpx.AsyncClient(
            headers=self._headers(),
            timeout=30.0,
            verify=False,
        )
        try:
            response = await self._client.get(f"{self.base_url}/v2/account")
            response.raise_for_status()
            self._connected = True
        except Exception as exc:
            if self._client:
                await self._client.aclose()
                self._client = None
            raise ConnectionError(f"Failed to connect to Alpaca: {exc}")

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        use_data_api: bool = False,
    ) -> dict[str, Any]:
        if not self._client:
            raise ConnectionError("Not connected to Alpaca")

        base_url = self.DATA_API_URL if use_data_api else self.base_url
        url = f"{base_url}{endpoint}"
        response = await self._client.request(
            method=method,
            url=url,
            params=params,
            json=data,
        )
        if response.status_code >= 400:
            raise Exception(f"Alpaca API error ({response.status_code}): {response.text}")
        if not response.content:
            return {}
        return response.json()

    def normalize_symbol(self, symbol: str) -> str:
        value = (symbol or "").strip().upper()
        if "/" in value:
            return value
        if "_" in value:
            parts = value.split("_")
            if len(parts) == 2 and len(parts[0]) == 3 and len(parts[1]) == 3:
                return f"{parts[0]}/{parts[1]}"
            return value.replace("_", "")
        return value

    def denormalize_symbol(self, symbol: str) -> str:
        value = (symbol or "").strip().upper()
        if "/" in value:
            return value.replace("/", "_")
        if len(value) == 6 and value[:3].isalpha() and value[3:].isalpha():
            return f"{value[:3]}_{value[3:]}"
        return value

    def _normalize_market_symbol(self, symbol: str) -> str:
        normalized = self.normalize_symbol(symbol)
        return normalized.replace("/", "")

    def _is_forex_like(self, symbol: str) -> bool:
        cleaned = symbol.replace("/", "").replace("_", "")
        return len(cleaned) == 6 and cleaned.isalpha()

    def _map_timeframe(self, timeframe: str) -> str:
        lookup = {
            "M1": "1Min",
            "M5": "5Min",
            "M15": "15Min",
            "M30": "30Min",
            "H1": "1Hour",
            "H4": "4Hour",
            "D": "1Day",
            "W": "1Week",
            "M": "1Month",
        }
        return lookup.get((timeframe or "").upper(), "5Min")

    def _parse_order_status(self, status: str) -> OrderStatus:
        value = (status or "").lower()
        if value in {"filled"}:
            return OrderStatus.FILLED
        if value in {"partially_filled"}:
            return OrderStatus.PARTIALLY_FILLED
        if value in {"canceled", "cancelled"}:
            return OrderStatus.CANCELLED
        if value in {"rejected"}:
            return OrderStatus.REJECTED
        if value in {"expired"}:
            return OrderStatus.EXPIRED
        return OrderStatus.PENDING

    def _parse_order_type(self, order_type: str) -> OrderType:
        value = (order_type or "").lower()
        if value == "limit":
            return OrderType.LIMIT
        if value == "stop":
            return OrderType.STOP
        if value == "stop_limit":
            return OrderType.STOP_LIMIT
        return OrderType.MARKET

    def _parse_order(self, payload: dict[str, Any]) -> OrderResult:
        qty = _to_decimal(payload.get("qty"), "0")
        filled_qty = _to_decimal(payload.get("filled_qty"), "0")
        side_value = (payload.get("side") or "buy").lower()
        side = OrderSide.SELL if side_value == "sell" else OrderSide.BUY
        return OrderResult(
            order_id=str(payload.get("id", "")),
            client_order_id=payload.get("client_order_id"),
            symbol=self.denormalize_symbol(str(payload.get("symbol", ""))),
            side=side,
            order_type=self._parse_order_type(str(payload.get("type", "market"))),
            status=self._parse_order_status(str(payload.get("status", "new"))),
            size=qty,
            filled_size=filled_qty,
            price=_to_decimal(payload.get("limit_price")) if payload.get("limit_price") else None,
            average_fill_price=(
                _to_decimal(payload.get("filled_avg_price"))
                if payload.get("filled_avg_price") is not None
                else None
            ),
            commission=Decimal("0"),
            created_at=_parse_iso_timestamp(payload.get("created_at")),
            filled_at=(
                _parse_iso_timestamp(payload.get("filled_at"))
                if payload.get("filled_at")
                else None
            ),
        )

    async def get_account_info(self) -> AccountInfo:
        payload = await self._request("GET", "/v2/account")
        leverage = int(_to_decimal(payload.get("multiplier"), "1"))
        return AccountInfo(
            account_id=str(payload.get("id", "")),
            balance=_to_decimal(payload.get("cash"), "0"),
            equity=_to_decimal(payload.get("equity"), "0"),
            margin_used=_to_decimal(payload.get("initial_margin"), "0"),
            margin_available=_to_decimal(payload.get("buying_power"), "0"),
            unrealized_pnl=_to_decimal(payload.get("unrealized_pl"), "0"),
            realized_pnl_today=Decimal("0"),
            currency=str(payload.get("currency", "USD")),
            leverage=max(1, leverage),
            updated_at=datetime.now(UTC),
        )

    async def get_instruments(self) -> list[Instrument]:
        payload = await self._request("GET", "/v2/assets", params={"status": "active"})
        instruments: list[Instrument] = []
        if isinstance(payload, list):
            for item in payload:
                symbol = str(item.get("symbol", "")).upper()
                if not symbol:
                    continue
                asset_class = str(item.get("class", "stock")).lower()
                instrument_type = "crypto" if asset_class == "crypto" else "stock"
                instruments.append(
                    Instrument(
                        symbol=symbol,
                        name=str(item.get("name") or symbol),
                        instrument_type=instrument_type,
                        min_size=Decimal("1"),
                        size_increment=Decimal("0.00000001") if instrument_type == "crypto" else Decimal("1"),
                        margin_rate=Decimal("0.5"),
                    )
                )
        return instruments

    async def place_order(self, order: OrderRequest) -> OrderResult:
        symbol = self.normalize_symbol(order.symbol)
        payload: dict[str, Any] = {
            "symbol": symbol,
            "qty": str(order.size),
            "side": "buy" if order.side == OrderSide.BUY else "sell",
            "type": {
                OrderType.MARKET: "market",
                OrderType.LIMIT: "limit",
                OrderType.STOP: "stop",
                OrderType.STOP_LIMIT: "stop_limit",
            }.get(order.order_type, "market"),
            "time_in_force": {
                TimeInForce.GTC: "gtc",
                TimeInForce.IOC: "ioc",
                TimeInForce.FOK: "fok",
                TimeInForce.DAY: "day",
            }.get(order.time_in_force, "gtc"),
        }

        if order.order_type in {OrderType.LIMIT, OrderType.STOP_LIMIT} and order.price is not None:
            payload["limit_price"] = str(order.price)
        if order.order_type in {OrderType.STOP, OrderType.STOP_LIMIT} and order.stop_price is not None:
            payload["stop_price"] = str(order.stop_price)
        if order.client_order_id:
            payload["client_order_id"] = order.client_order_id

        # Bracket orders in Alpaca require both TP and SL.
        if order.stop_loss is not None and order.take_profit is not None:
            payload["order_class"] = "bracket"
            payload["stop_loss"] = {"stop_price": str(order.stop_loss)}
            payload["take_profit"] = {"limit_price": str(order.take_profit)}

        result = await self._request("POST", "/v2/orders", data=payload)
        return self._parse_order(result)

    async def cancel_order(self, order_id: str) -> bool:
        try:
            await self._request("DELETE", f"/v2/orders/{order_id}")
            return True
        except Exception:
            return False

    async def get_order(self, order_id: str) -> OrderResult | None:
        try:
            payload = await self._request("GET", f"/v2/orders/{order_id}")
            return self._parse_order(payload)
        except Exception:
            return None

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        params: dict[str, Any] = {"status": "open", "nested": "true"}
        if symbol:
            params["symbols"] = self.normalize_symbol(symbol)
        payload = await self._request("GET", "/v2/orders", params=params)
        if not isinstance(payload, list):
            return []
        return [self._parse_order(item) for item in payload]

    async def get_positions(self) -> list[Position]:
        payload = await self._request("GET", "/v2/positions")
        if not isinstance(payload, list):
            return []

        positions: list[Position] = []
        for item in payload:
            qty = _to_decimal(item.get("qty"), "0")
            side_raw = str(item.get("side", "long")).lower()
            side = PositionSide.SHORT if side_raw == "short" else PositionSide.LONG
            entry_price = _to_decimal(item.get("avg_entry_price"), "0")
            current_price = _to_decimal(item.get("current_price"), "0")
            market_value = _to_decimal(item.get("market_value"), "0")
            positions.append(
                Position(
                    position_id=str(item.get("asset_id", item.get("symbol", ""))),
                    symbol=self.denormalize_symbol(str(item.get("symbol", ""))),
                    side=side,
                    size=abs(qty),
                    entry_price=entry_price,
                    current_price=current_price,
                    unrealized_pnl=_to_decimal(item.get("unrealized_pl"), "0"),
                    margin_used=abs(market_value),
                    leverage=1,
                    stop_loss=None,
                    take_profit=None,
                    opened_at=datetime.now(UTC),
                )
            )
        return positions

    async def get_position(self, symbol: str) -> Position | None:
        target = self._normalize_market_symbol(symbol)
        try:
            payload = await self._request("GET", f"/v2/positions/{target}")
            all_positions = await self.get_positions()
            for position in all_positions:
                if self._normalize_market_symbol(position.symbol) == target:
                    return position
            qty = _to_decimal(payload.get("qty"), "0")
            if qty == 0:
                return None
            side = PositionSide.SHORT if str(payload.get("side", "long")).lower() == "short" else PositionSide.LONG
            return Position(
                position_id=str(payload.get("asset_id", payload.get("symbol", ""))),
                symbol=self.denormalize_symbol(str(payload.get("symbol", ""))),
                side=side,
                size=abs(qty),
                entry_price=_to_decimal(payload.get("avg_entry_price"), "0"),
                current_price=_to_decimal(payload.get("current_price"), "0"),
                unrealized_pnl=_to_decimal(payload.get("unrealized_pl"), "0"),
                margin_used=abs(_to_decimal(payload.get("market_value"), "0")),
                leverage=1,
                opened_at=datetime.now(UTC),
            )
        except Exception:
            return None

    async def close_position(
        self,
        symbol: str,
        size: Decimal | None = None,
    ) -> OrderResult:
        target = self._normalize_market_symbol(symbol)
        params: dict[str, Any] = {}
        if size is not None:
            params["qty"] = str(size)
        payload = await self._request("DELETE", f"/v2/positions/{target}", params=params)
        if isinstance(payload, dict) and payload.get("id"):
            return self._parse_order(payload)

        # API can return just status payload in some cases.
        return OrderResult(
            order_id=f"close-{target}-{int(datetime.now(UTC).timestamp())}",
            symbol=self.denormalize_symbol(target),
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            status=OrderStatus.FILLED,
            size=size or Decimal("0"),
            filled_size=size or Decimal("0"),
            average_fill_price=None,
            created_at=datetime.now(UTC),
            filled_at=datetime.now(UTC),
        )

    async def modify_position(
        self,
        symbol: str,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
    ) -> bool:
        # Alpaca does not expose a direct position SL/TP modification endpoint.
        # This can be done only via replacing open stop/limit orders.
        if stop_loss is None and take_profit is None:
            return True
        return False

    async def get_current_price(self, symbol: str) -> Tick:
        normalized = self.normalize_symbol(symbol)

        # Forex-like pairs are requested from crypto feed if supported.
        if "/" in normalized or self._is_forex_like(normalized):
            pair = normalized if "/" in normalized else f"{normalized[:3]}/{normalized[3:]}"
            try:
                payload = await self._request(
                    "GET",
                    "/v1beta3/crypto/us/latest/quotes",
                    params={"symbols": pair},
                    use_data_api=True,
                )
                quote = (payload.get("quotes") or {}).get(pair) or {}
                bid = _to_decimal(quote.get("bp"), "0")
                ask = _to_decimal(quote.get("ap"), "0")
                if bid > 0 and ask > 0:
                    return Tick(
                        symbol=self.denormalize_symbol(pair),
                        bid=bid,
                        ask=ask,
                        timestamp=_parse_iso_timestamp(quote.get("t")),
                    )
            except Exception:
                pass

        stock_symbol = self._normalize_market_symbol(normalized)
        payload = await self._request(
            "GET",
            f"/v2/stocks/{stock_symbol}/quotes/latest",
            use_data_api=True,
        )
        quote = payload.get("quote") or {}
        bid = _to_decimal(quote.get("bp"), "0")
        ask = _to_decimal(quote.get("ap"), "0")
        if bid <= 0 or ask <= 0:
            trade_payload = await self._request(
                "GET",
                f"/v2/stocks/{stock_symbol}/trades/latest",
                use_data_api=True,
            )
            trade = trade_payload.get("trade") or {}
            price = _to_decimal(trade.get("p"), "0")
            bid = price
            ask = price
            timestamp = _parse_iso_timestamp(trade.get("t"))
        else:
            timestamp = _parse_iso_timestamp(quote.get("t"))

        return Tick(
            symbol=self.denormalize_symbol(stock_symbol),
            bid=bid,
            ask=ask,
            timestamp=timestamp,
        )

    async def get_prices(self, symbols: list[str]) -> dict[str, Tick]:
        result: dict[str, Tick] = {}
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
        normalized = self.normalize_symbol(symbol)
        tf = self._map_timeframe(timeframe)
        safe_count = max(1, min(int(count or 100), 1000))
        params: dict[str, Any] = {"timeframe": tf, "limit": safe_count}
        if from_time:
            params["start"] = from_time.astimezone(UTC).isoformat().replace("+00:00", "Z")
        if to_time:
            params["end"] = to_time.astimezone(UTC).isoformat().replace("+00:00", "Z")

        candles: list[Candle] = []

        if "/" in normalized or self._is_forex_like(normalized):
            pair = normalized if "/" in normalized else f"{normalized[:3]}/{normalized[3:]}"
            payload = await self._request(
                "GET",
                "/v1beta3/crypto/us/bars",
                params={**params, "symbols": pair},
                use_data_api=True,
            )
            bars = ((payload.get("bars") or {}).get(pair)) or []
            for bar in bars:
                candles.append(
                    Candle(
                        symbol=self.denormalize_symbol(pair),
                        timestamp=_parse_iso_timestamp(bar.get("t")),
                        open=_to_decimal(bar.get("o"), "0"),
                        high=_to_decimal(bar.get("h"), "0"),
                        low=_to_decimal(bar.get("l"), "0"),
                        close=_to_decimal(bar.get("c"), "0"),
                        volume=_to_decimal(bar.get("v"), "0"),
                        timeframe=timeframe,
                    )
                )
            return candles

        stock_symbol = self._normalize_market_symbol(normalized)
        payload = await self._request(
            "GET",
            f"/v2/stocks/{stock_symbol}/bars",
            params=params,
            use_data_api=True,
        )
        for bar in payload.get("bars", []):
            candles.append(
                Candle(
                    symbol=self.denormalize_symbol(stock_symbol),
                    timestamp=_parse_iso_timestamp(bar.get("t")),
                    open=_to_decimal(bar.get("o"), "0"),
                    high=_to_decimal(bar.get("h"), "0"),
                    low=_to_decimal(bar.get("l"), "0"),
                    close=_to_decimal(bar.get("c"), "0"),
                    volume=_to_decimal(bar.get("v"), "0"),
                    timeframe=timeframe,
                )
            )
        return candles
