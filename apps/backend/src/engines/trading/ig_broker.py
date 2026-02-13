"""
IG Broker Implementation

Implements BaseBroker using IG Markets REST API.
Supports demo and live environments.
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
    try:
        return datetime.strptime(text, "%Y:%m:%d-%H:%M:%S").replace(tzinfo=UTC)
    except Exception:
        return datetime.now(UTC)


class IGBroker(BaseBroker):
    """IG Markets broker implementation."""

    DEMO_BASE_URL = "https://demo-api.ig.com/gateway/deal"
    LIVE_BASE_URL = "https://api.ig.com/gateway/deal"

    # Known mapping for common symbols. Users can also pass an epic directly in symbols.
    SYMBOL_TO_EPIC = {
        "EUR_USD": "CS.D.EURUSD.CFD.IP",
        "GBP_USD": "CS.D.GBPUSD.CFD.IP",
        "USD_JPY": "CS.D.USDJPY.CFD.IP",
        "USD_CHF": "CS.D.USDCHF.CFD.IP",
        "AUD_USD": "CS.D.AUDUSD.CFD.IP",
        "USD_CAD": "CS.D.USDCAD.CFD.IP",
        "NZD_USD": "CS.D.NZDUSD.CFD.IP",
        "EUR_GBP": "CS.D.EURGBP.CFD.IP",
        "EUR_JPY": "CS.D.EURJPY.CFD.IP",
        "GBP_JPY": "CS.D.GBPJPY.CFD.IP",
        "XAU_USD": "CS.D.GC.CFD.IP",
        "XAG_USD": "CS.D.SI.CFD.IP",
        "US500": "IX.D.SPTRD.CASH.IP",
        "US30": "IX.D.DOW.CASH.IP",
        "NAS100": "IX.D.NASDAQ.CASH.IP",
        "DE40": "IX.D.DAX.CASH.IP",
        "UK100": "IX.D.FTSE.CASH.IP",
        "JP225": "IX.D.NIKKEI.CASH.IP",
    }
    EPIC_TO_SYMBOL = {v: k for k, v in SYMBOL_TO_EPIC.items()}

    def __init__(
        self,
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
        account_id: str | None = None,
        environment: str = "demo",
    ):
        super().__init__()
        self.api_key = api_key or settings.IG_API_KEY
        self.username = username or settings.IG_USERNAME
        self.password = password or settings.IG_PASSWORD
        self.account_id = account_id or settings.IG_ACCOUNT_ID
        self.environment = (environment or settings.IG_ENVIRONMENT or "demo").lower()
        if not self.api_key:
            raise ValueError("IG API key is required")
        if not self.username:
            raise ValueError("IG username is required")
        if not self.password:
            raise ValueError("IG password is required")

        self.base_url = self.LIVE_BASE_URL if self.environment == "live" else self.DEMO_BASE_URL
        self._client: httpx.AsyncClient | None = None
        self._cst: str | None = None
        self._security_token: str | None = None

    @property
    def name(self) -> str:
        return "IG"

    @property
    def supported_markets(self) -> list[str]:
        return ["forex", "indices", "commodities", "stocks", "crypto"]

    def normalize_symbol(self, symbol: str) -> str:
        value = (symbol or "").strip().upper().replace("/", "_")
        if "." in value:
            return value
        return value

    def denormalize_symbol(self, symbol: str) -> str:
        value = (symbol or "").strip().upper()
        if value in self.EPIC_TO_SYMBOL:
            return self.EPIC_TO_SYMBOL[value]
        return value

    def _resolve_epic(self, symbol: str) -> str:
        normalized = self.normalize_symbol(symbol)
        if "." in normalized:
            return normalized
        return self.SYMBOL_TO_EPIC.get(normalized, normalized)

    def _base_headers(self, version: str = "2") -> dict[str, str]:
        headers = {
            "X-IG-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Version": version,
        }
        if self.account_id:
            headers["IG-ACCOUNT-ID"] = self.account_id
        return headers

    def _auth_headers(self, version: str = "2") -> dict[str, str]:
        headers = self._base_headers(version=version)
        if self._cst:
            headers["CST"] = self._cst
        if self._security_token:
            headers["X-SECURITY-TOKEN"] = self._security_token
        return headers

    async def connect(self) -> None:
        if self._connected:
            return

        self._client = httpx.AsyncClient(timeout=30.0, verify=False)
        payload = {
            "identifier": self.username,
            "password": self.password,
            "encryptedPassword": False,
        }
        response = await self._client.post(
            f"{self.base_url}/session",
            headers=self._base_headers(version="2"),
            json=payload,
        )
        if response.status_code >= 400:
            await self._client.aclose()
            self._client = None
            raise ConnectionError(f"Failed to connect to IG: {response.status_code} {response.text}")

        self._cst = response.headers.get("CST")
        self._security_token = response.headers.get("X-SECURITY-TOKEN")
        if not self._cst or not self._security_token:
            await self._client.aclose()
            self._client = None
            raise ConnectionError("IG session tokens not returned by API")

        body = response.json() if response.content else {}
        active_account = body.get("currentAccountId")
        if not self.account_id:
            self.account_id = active_account

        # Switch account when API credentials are tied to a specific account.
        if self.account_id and active_account and self.account_id != active_account:
            try:
                await self._client.put(
                    f"{self.base_url}/session",
                    headers=self._auth_headers(version="1"),
                    json={"accountId": self.account_id, "defaultAccount": True},
                )
            except Exception:
                pass

        self._connected = True

    async def disconnect(self) -> None:
        if self._client:
            try:
                if self._connected and self._cst and self._security_token:
                    await self._client.delete(
                        f"{self.base_url}/session",
                        headers=self._auth_headers(version="1"),
                    )
            except Exception:
                pass
            await self._client.aclose()
            self._client = None
        self._cst = None
        self._security_token = None
        self._connected = False

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        version: str = "2",
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self._client:
            raise ConnectionError("Not connected to IG")
        response = await self._client.request(
            method=method,
            url=f"{self.base_url}{endpoint}",
            headers=self._auth_headers(version=version),
            params=params,
            json=data,
        )
        if response.status_code >= 400:
            raise Exception(f"IG API error ({response.status_code}): {response.text}")
        if not response.content:
            return {}
        return response.json()

    def _parse_order_status(self, payload: dict[str, Any]) -> OrderStatus:
        deal_status = str(payload.get("dealStatus", payload.get("status", ""))).upper()
        if deal_status in {"ACCEPTED", "OPEN"}:
            return OrderStatus.FILLED
        if deal_status in {"PARTIALLY_ACCEPTED"}:
            return OrderStatus.PARTIALLY_FILLED
        if deal_status in {"REJECTED"}:
            return OrderStatus.REJECTED
        if deal_status in {"DELETED", "CANCELLED"}:
            return OrderStatus.CANCELLED
        return OrderStatus.PENDING

    def _parse_order_type(self, value: str) -> OrderType:
        order_type = (value or "").upper()
        if order_type == "LIMIT":
            return OrderType.LIMIT
        if order_type == "STOP":
            return OrderType.STOP
        return OrderType.MARKET

    async def _confirm_deal(self, deal_reference: str) -> dict[str, Any]:
        return await self._request("GET", f"/confirms/{deal_reference}", version="1")

    async def get_account_info(self) -> AccountInfo:
        payload = await self._request("GET", "/accounts", version="1")
        accounts = payload.get("accounts", [])
        selected = None
        for account in accounts:
            if self.account_id and str(account.get("accountId")) == str(self.account_id):
                selected = account
                break
        if selected is None and accounts:
            selected = accounts[0]
            if not self.account_id:
                self.account_id = selected.get("accountId")
        if selected is None:
            raise Exception("No IG account returned by API")

        balance = selected.get("balance", {}) or {}
        available = _to_decimal(balance.get("available"), "0")
        pnl = _to_decimal(balance.get("profitLoss"), "0")
        cash = _to_decimal(balance.get("balance"), "0")
        equity = cash + pnl
        deposit = _to_decimal(balance.get("deposit"), "0")

        return AccountInfo(
            account_id=str(selected.get("accountId", "")),
            balance=cash,
            equity=equity,
            margin_used=deposit,
            margin_available=available,
            unrealized_pnl=pnl,
            realized_pnl_today=Decimal("0"),
            currency=str(selected.get("currency", "USD")),
            leverage=1,
            updated_at=datetime.now(UTC),
        )

    async def get_instruments(self) -> list[Instrument]:
        instruments: list[Instrument] = []
        for symbol, epic in self.SYMBOL_TO_EPIC.items():
            inst_type = "forex"
            if symbol in {"US500", "US30", "NAS100", "DE40", "UK100", "JP225"}:
                inst_type = "indices"
            if symbol in {"XAU_USD", "XAG_USD"}:
                inst_type = "commodities"
            instruments.append(
                Instrument(
                    symbol=symbol,
                    name=epic,
                    instrument_type=inst_type,
                    min_size=Decimal("0.1"),
                    size_increment=Decimal("0.1"),
                    margin_rate=Decimal("0.05"),
                )
            )
        return instruments

    async def place_order(self, order: OrderRequest) -> OrderResult:
        epic = self._resolve_epic(order.symbol)
        payload: dict[str, Any] = {
            "epic": epic,
            "expiry": "-",
            "direction": "BUY" if order.side == OrderSide.BUY else "SELL",
            "size": float(order.size),
            "forceOpen": True,
            "orderType": {
                OrderType.MARKET: "MARKET",
                OrderType.LIMIT: "LIMIT",
                OrderType.STOP: "STOP",
                OrderType.STOP_LIMIT: "LIMIT",
            }.get(order.order_type, "MARKET"),
            "timeInForce": {
                TimeInForce.GTC: "GOOD_TILL_CANCELLED",
                TimeInForce.IOC: "EXECUTE_AND_ELIMINATE",
                TimeInForce.FOK: "FILL_OR_KILL",
                TimeInForce.DAY: "GOOD_TILL_DATE",
            }.get(order.time_in_force, "FILL_OR_KILL"),
            "currencyCode": "USD",
            "guaranteedStop": False,
        }
        if order.order_type in {OrderType.LIMIT, OrderType.STOP_LIMIT} and order.price is not None:
            payload["level"] = float(order.price)
        if order.order_type == OrderType.STOP and order.stop_price is not None:
            payload["level"] = float(order.stop_price)
        if order.stop_loss is not None:
            payload["stopLevel"] = float(order.stop_loss)
        if order.take_profit is not None:
            payload["limitLevel"] = float(order.take_profit)

        result = await self._request("POST", "/positions/otc", version="2", data=payload)
        deal_reference = str(result.get("dealReference", ""))
        if not deal_reference:
            return OrderResult(
                order_id="",
                symbol=self.denormalize_symbol(epic),
                side=order.side,
                order_type=order.order_type,
                status=OrderStatus.REJECTED,
                size=order.size,
                filled_size=Decimal("0"),
                error_message=f"IG order placement failed: {result}",
            )

        confirmation = await self._confirm_deal(deal_reference)
        status = self._parse_order_status(confirmation)
        average_price = confirmation.get("level")
        deal_id = str(confirmation.get("dealId") or deal_reference)
        return OrderResult(
            order_id=deal_id,
            client_order_id=order.client_order_id,
            symbol=self.denormalize_symbol(epic),
            side=order.side,
            order_type=order.order_type,
            status=status,
            size=order.size,
            filled_size=order.size if status == OrderStatus.FILLED else Decimal("0"),
            price=order.price,
            average_fill_price=_to_decimal(average_price) if average_price is not None else None,
            commission=Decimal("0"),
            created_at=datetime.now(UTC),
            filled_at=datetime.now(UTC) if status == OrderStatus.FILLED else None,
            error_message=confirmation.get("reason") if status == OrderStatus.REJECTED else None,
        )

    async def cancel_order(self, order_id: str) -> bool:
        try:
            await self._request("DELETE", f"/workingorders/otc/{order_id}", version="2")
            return True
        except Exception:
            return False

    async def get_order(self, order_id: str) -> OrderResult | None:
        # IG does not expose a straightforward single-order endpoint by deal id for all order types.
        # We scan working orders and return if present.
        for order in await self.get_open_orders():
            if order.order_id == order_id:
                return order
        return None

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        payload = await self._request("GET", "/workingorders", version="2")
        epic_filter = self._resolve_epic(symbol) if symbol else None
        results: list[OrderResult] = []
        for item in payload.get("workingOrders", []):
            market = item.get("marketData", {}) or {}
            order = item.get("workingOrderData", {}) or {}
            epic = str(market.get("epic", ""))
            if epic_filter and epic != epic_filter:
                continue
            direction = str(order.get("direction", "BUY")).upper()
            side = OrderSide.SELL if direction == "SELL" else OrderSide.BUY
            order_type = self._parse_order_type(str(order.get("orderType", "LIMIT")))
            size = _to_decimal(order.get("size"), "0")
            results.append(
                OrderResult(
                    order_id=str(order.get("dealId", order.get("dealReference", ""))),
                    symbol=self.denormalize_symbol(epic),
                    side=side,
                    order_type=order_type,
                    status=OrderStatus.PENDING,
                    size=size,
                    filled_size=Decimal("0"),
                    price=_to_decimal(order.get("level")) if order.get("level") is not None else None,
                    created_at=_parse_timestamp(order.get("createdDate", datetime.now(UTC).isoformat())),
                )
            )
        return results

    async def get_positions(self) -> list[Position]:
        payload = await self._request("GET", "/positions", version="2")
        positions: list[Position] = []
        for item in payload.get("positions", []):
            market = item.get("market", {}) or {}
            position_data = item.get("position", {}) or {}
            epic = str(market.get("epic", ""))
            size = _to_decimal(position_data.get("size"), "0")
            if size == 0:
                continue
            direction = str(position_data.get("direction", "BUY")).upper()
            side = PositionSide.SHORT if direction == "SELL" else PositionSide.LONG
            bid = _to_decimal(market.get("bid"), "0")
            offer = _to_decimal(market.get("offer"), "0")
            current_price = offer if side == PositionSide.LONG else bid
            if current_price <= 0:
                current_price = _to_decimal(position_data.get("level"), "0")
            positions.append(
                Position(
                    position_id=str(position_data.get("dealId", epic)),
                    symbol=self.denormalize_symbol(epic),
                    side=side,
                    size=abs(size),
                    entry_price=_to_decimal(position_data.get("level"), "0"),
                    current_price=current_price,
                    unrealized_pnl=_to_decimal(position_data.get("profit"), "0"),
                    margin_used=_to_decimal(position_data.get("margin"), "0"),
                    leverage=1,
                    stop_loss=(
                        _to_decimal(position_data.get("stopLevel"))
                        if position_data.get("stopLevel") is not None
                        else None
                    ),
                    take_profit=(
                        _to_decimal(position_data.get("limitLevel"))
                        if position_data.get("limitLevel") is not None
                        else None
                    ),
                    opened_at=_parse_timestamp(position_data.get("createdDateUTC")),
                )
            )
        return positions

    async def get_position(self, symbol: str) -> Position | None:
        target = self._resolve_epic(symbol)
        for position in await self.get_positions():
            if self._resolve_epic(position.symbol) == target:
                return position
        return None

    async def close_position(
        self,
        symbol: str,
        size: Decimal | None = None,
    ) -> OrderResult:
        target_epic = self._resolve_epic(symbol)
        position = None
        for candidate in await self.get_positions():
            if self._resolve_epic(candidate.symbol) == target_epic:
                position = candidate
                break
        if not position:
            raise ValueError(f"No open position found for {symbol}")

        close_size = size or position.size
        direction = "BUY" if position.side == PositionSide.SHORT else "SELL"
        payload = {
            "dealId": position.position_id,
            "direction": direction,
            "size": float(close_size),
            "orderType": "MARKET",
            "timeInForce": "FILL_OR_KILL",
        }
        result = await self._request("DELETE", "/positions/otc", version="1", data=payload)
        deal_reference = str(result.get("dealReference", ""))
        if not deal_reference:
            return OrderResult(
                order_id="",
                symbol=self.denormalize_symbol(target_epic),
                side=OrderSide.SELL if direction == "SELL" else OrderSide.BUY,
                order_type=OrderType.MARKET,
                status=OrderStatus.REJECTED,
                size=close_size,
                filled_size=Decimal("0"),
                error_message=f"IG close failed: {result}",
            )
        confirmation = await self._confirm_deal(deal_reference)
        status = self._parse_order_status(confirmation)
        return OrderResult(
            order_id=str(confirmation.get("dealId", deal_reference)),
            symbol=self.denormalize_symbol(target_epic),
            side=OrderSide.SELL if direction == "SELL" else OrderSide.BUY,
            order_type=OrderType.MARKET,
            status=status,
            size=close_size,
            filled_size=close_size if status == OrderStatus.FILLED else Decimal("0"),
            average_fill_price=(
                _to_decimal(confirmation.get("level"))
                if confirmation.get("level") is not None
                else None
            ),
            created_at=datetime.now(UTC),
            filled_at=datetime.now(UTC) if status == OrderStatus.FILLED else None,
            error_message=confirmation.get("reason") if status == OrderStatus.REJECTED else None,
        )

    async def modify_position(
        self,
        symbol: str,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
    ) -> bool:
        position = await self.get_position(symbol)
        if not position:
            return False
        payload: dict[str, Any] = {}
        if stop_loss is not None:
            payload["stopLevel"] = float(stop_loss)
        if take_profit is not None:
            payload["limitLevel"] = float(take_profit)
        if not payload:
            return True
        await self._request(
            "PUT",
            f"/positions/otc/{position.position_id}",
            version="2",
            data=payload,
        )
        return True

    async def get_current_price(self, symbol: str) -> Tick:
        epic = self._resolve_epic(symbol)
        payload = await self._request("GET", f"/markets/{epic}", version="3")
        snapshot = payload.get("snapshot", {}) or {}
        bid = _to_decimal(snapshot.get("bid"), "0")
        ask = _to_decimal(snapshot.get("offer"), "0")
        if bid <= 0 or ask <= 0:
            raise ValueError(f"Invalid market snapshot for {epic}")
        return Tick(
            symbol=self.denormalize_symbol(epic),
            bid=bid,
            ask=ask,
            timestamp=_parse_timestamp(snapshot.get("updateTimeUTC")),
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

    def _map_timeframe(self, timeframe: str) -> str:
        return {
            "M1": "MINUTE",
            "M5": "MINUTE_5",
            "M15": "MINUTE_15",
            "M30": "MINUTE_30",
            "H1": "HOUR",
            "H4": "HOUR_4",
            "D": "DAY",
            "W": "WEEK",
            "M": "MONTH",
        }.get((timeframe or "").upper(), "MINUTE_5")

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        count: int = 100,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> list[Candle]:
        epic = self._resolve_epic(symbol)
        params: dict[str, Any] = {
            "resolution": self._map_timeframe(timeframe),
            "max": max(1, min(int(count or 100), 1000)),
        }
        if from_time:
            params["from"] = from_time.astimezone(UTC).isoformat().replace("+00:00", "")
        if to_time:
            params["to"] = to_time.astimezone(UTC).isoformat().replace("+00:00", "")

        payload = await self._request("GET", f"/prices/{epic}", version="3", params=params)
        candles: list[Candle] = []
        for item in payload.get("prices", []):
            open_price = item.get("openPrice", {}) or {}
            high_price = item.get("highPrice", {}) or {}
            low_price = item.get("lowPrice", {}) or {}
            close_price = item.get("closePrice", {}) or {}
            candles.append(
                Candle(
                    symbol=self.denormalize_symbol(epic),
                    timestamp=_parse_timestamp(item.get("snapshotTimeUTC")),
                    open=_to_decimal(open_price.get("bid"), "0"),
                    high=_to_decimal(high_price.get("bid"), "0"),
                    low=_to_decimal(low_price.get("bid"), "0"),
                    close=_to_decimal(close_price.get("bid"), "0"),
                    volume=_to_decimal(item.get("lastTradedVolume"), "0"),
                    timeframe=timeframe,
                )
            )
        return candles
