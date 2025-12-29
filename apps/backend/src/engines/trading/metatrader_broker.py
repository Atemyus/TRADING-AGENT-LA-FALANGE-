"""
MetaTrader Broker Implementation

Connects to MetaTrader 4/5 via MetaApi.cloud REST API.
Supports any MT4/MT5 broker (IC Markets, Pepperstone, XM, etc.)

Setup:
1. Create account at https://metaapi.cloud
2. Add your MT4/MT5 account to MetaApi
3. Get your access token and account ID
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from src.core.config import settings
from src.engines.trading.base_broker import (
    AccountInfo,
    BaseBroker,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Tick,
)


class MetaTraderBroker(BaseBroker):
    """
    MetaTrader 4/5 broker via MetaApi.cloud

    MetaApi provides a REST API to interact with MT4/MT5 accounts
    without needing to run Expert Advisors or connect via DLL.

    Supported brokers: Any MT4/MT5 broker
    - IC Markets
    - Pepperstone
    - XM
    - FXCM
    - Admiral Markets
    - And many more...
    """

    BASE_URL = "https://mt-client-api-v1.agiliumtrade.agiliumtrade.ai"
    PROVISIONING_URL = "https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai"

    def __init__(
        self,
        access_token: Optional[str] = None,
        account_id: Optional[str] = None,
    ):
        """
        Initialize MetaTrader broker.

        Args:
            access_token: MetaApi access token
            account_id: MetaApi account ID (not MT4/MT5 login)
        """
        self.access_token = access_token or getattr(settings, 'METAAPI_ACCESS_TOKEN', None)
        self.account_id = account_id or getattr(settings, 'METAAPI_ACCOUNT_ID', None)
        self._client: Optional[httpx.AsyncClient] = None
        self._account_info: Optional[Dict[str, Any]] = None
        self._connected = False

    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "auth-token": self.access_token,
                    "Content-Type": "application/json",
                },
            )

    async def _request(
        self,
        method: str,
        endpoint: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make API request."""
        await self._ensure_client()

        url = f"{base_url or self.BASE_URL}{endpoint}"
        response = await self._client.request(method, url, **kwargs)

        if response.status_code >= 400:
            error_text = response.text
            raise Exception(f"MetaApi error ({response.status_code}): {error_text}")

        if response.status_code == 204:
            return {}

        return response.json()

    async def connect(self) -> None:
        """Connect to MetaTrader account via MetaApi."""
        if not self.access_token:
            raise ValueError("MetaApi access token not configured")
        if not self.account_id:
            raise ValueError("MetaApi account ID not configured")

        await self._ensure_client()

        # Get account info to verify connection
        try:
            # First, ensure account is deployed
            account = await self._request(
                "GET",
                f"/users/current/accounts/{self.account_id}",
                base_url=self.PROVISIONING_URL,
            )

            if account.get("state") != "DEPLOYED":
                # Deploy the account if not deployed
                await self._request(
                    "POST",
                    f"/users/current/accounts/{self.account_id}/deploy",
                    base_url=self.PROVISIONING_URL,
                )
                # Wait for deployment
                await asyncio.sleep(5)

            # Get account information
            self._account_info = await self._request(
                "GET",
                f"/users/current/accounts/{self.account_id}/account-information",
            )

            self._connected = True

        except Exception as e:
            raise Exception(f"Failed to connect to MetaTrader: {e}")

    async def disconnect(self) -> None:
        """Disconnect from MetaApi."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    @property
    def broker_name(self) -> str:
        """Get broker name."""
        return "metatrader"

    async def get_account_info(self) -> AccountInfo:
        """Get account information."""
        if not self._connected:
            await self.connect()

        info = await self._request(
            "GET",
            f"/users/current/accounts/{self.account_id}/account-information",
        )

        return AccountInfo(
            account_id=self.account_id,
            balance=Decimal(str(info.get("balance", 0))),
            equity=Decimal(str(info.get("equity", 0))),
            margin_used=Decimal(str(info.get("margin", 0))),
            margin_available=Decimal(str(info.get("freeMargin", 0))),
            unrealized_pnl=Decimal(str(info.get("equity", 0) - info.get("balance", 0))),
            currency=info.get("currency", "USD"),
            leverage=info.get("leverage", 1),
        )

    async def get_positions(self) -> List[Position]:
        """Get all open positions."""
        if not self._connected:
            await self.connect()

        positions_data = await self._request(
            "GET",
            f"/users/current/accounts/{self.account_id}/positions",
        )

        positions = []
        for pos in positions_data:
            positions.append(Position(
                position_id=str(pos.get("id")),
                symbol=pos.get("symbol", ""),
                side=OrderSide.BUY if pos.get("type") == "POSITION_TYPE_BUY" else OrderSide.SELL,
                size=Decimal(str(abs(pos.get("volume", 0)))),
                entry_price=Decimal(str(pos.get("openPrice", 0))),
                current_price=Decimal(str(pos.get("currentPrice", 0))),
                unrealized_pnl=Decimal(str(pos.get("profit", 0))),
                margin_used=Decimal(str(pos.get("margin", 0))),
                stop_loss=Decimal(str(pos.get("stopLoss", 0))) if pos.get("stopLoss") else None,
                take_profit=Decimal(str(pos.get("takeProfit", 0))) if pos.get("takeProfit") else None,
                opened_at=datetime.fromisoformat(pos.get("time", datetime.now().isoformat()).replace("Z", "+00:00")),
            ))

        return positions

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        positions = await self.get_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return pos
        return None

    async def place_order(self, order: OrderRequest) -> OrderResult:
        """Place a trading order."""
        if not self._connected:
            await self.connect()

        # Map order type
        action_type = "ORDER_TYPE_BUY" if order.side == OrderSide.BUY else "ORDER_TYPE_SELL"

        if order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY:
                action_type = "ORDER_TYPE_BUY_LIMIT"
            else:
                action_type = "ORDER_TYPE_SELL_LIMIT"
        elif order.order_type == OrderType.STOP:
            if order.side == OrderSide.BUY:
                action_type = "ORDER_TYPE_BUY_STOP"
            else:
                action_type = "ORDER_TYPE_SELL_STOP"

        # Build order payload
        payload = {
            "symbol": order.symbol,
            "actionType": action_type,
            "volume": float(order.size),
        }

        # Add price for limit/stop orders
        if order.order_type in [OrderType.LIMIT, OrderType.STOP] and order.price:
            payload["openPrice"] = float(order.price)

        # Add SL/TP
        if order.stop_loss:
            payload["stopLoss"] = float(order.stop_loss)
        if order.take_profit:
            payload["takeProfit"] = float(order.take_profit)

        try:
            result = await self._request(
                "POST",
                f"/users/current/accounts/{self.account_id}/trade",
                json=payload,
            )

            return OrderResult(
                order_id=str(result.get("orderId", result.get("positionId", ""))),
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                status=OrderStatus.FILLED if result.get("positionId") else OrderStatus.PENDING,
                size=order.size,
                filled_size=order.size if result.get("positionId") else Decimal("0"),
                price=order.price,
                average_fill_price=Decimal(str(result.get("openPrice", 0))) if result.get("openPrice") else None,
                commission=Decimal(str(result.get("commission", 0))),
            )

        except Exception as e:
            return OrderResult(
                order_id="",
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                status=OrderStatus.REJECTED,
                size=order.size,
                filled_size=Decimal("0"),
                error_message=str(e),
            )

    async def close_position(
        self,
        symbol: str,
        size: Optional[Decimal] = None
    ) -> OrderResult:
        """Close a position."""
        if not self._connected:
            await self.connect()

        # Get the position first
        position = await self.get_position(symbol)
        if not position:
            return OrderResult(
                order_id="",
                symbol=symbol,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                status=OrderStatus.REJECTED,
                size=Decimal("0"),
                filled_size=Decimal("0"),
                error_message="Position not found",
            )

        close_size = size or position.size

        # Close by placing opposite order
        payload = {
            "actionType": "POSITION_CLOSE_ID",
            "positionId": position.position_id,
        }

        if size and size < position.size:
            # Partial close
            payload["volume"] = float(size)

        try:
            result = await self._request(
                "POST",
                f"/users/current/accounts/{self.account_id}/trade",
                json=payload,
            )

            return OrderResult(
                order_id=str(result.get("orderId", "")),
                symbol=symbol,
                side=OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY,
                order_type=OrderType.MARKET,
                status=OrderStatus.FILLED,
                size=close_size,
                filled_size=close_size,
                average_fill_price=Decimal(str(result.get("closePrice", 0))) if result.get("closePrice") else None,
            )

        except Exception as e:
            return OrderResult(
                order_id="",
                symbol=symbol,
                side=OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY,
                order_type=OrderType.MARKET,
                status=OrderStatus.REJECTED,
                size=close_size,
                filled_size=Decimal("0"),
                error_message=str(e),
            )

    async def modify_position(
        self,
        symbol: str,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
    ) -> bool:
        """Modify position SL/TP."""
        if not self._connected:
            await self.connect()

        position = await self.get_position(symbol)
        if not position:
            return False

        payload = {
            "actionType": "POSITION_MODIFY",
            "positionId": position.position_id,
        }

        if stop_loss is not None:
            payload["stopLoss"] = float(stop_loss)
        if take_profit is not None:
            payload["takeProfit"] = float(take_profit)

        try:
            await self._request(
                "POST",
                f"/users/current/accounts/{self.account_id}/trade",
                json=payload,
            )
            return True
        except Exception:
            return False

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        if not self._connected:
            await self.connect()

        try:
            await self._request(
                "POST",
                f"/users/current/accounts/{self.account_id}/trade",
                json={
                    "actionType": "ORDER_CANCEL",
                    "orderId": order_id,
                },
            )
            return True
        except Exception:
            return False

    async def get_pending_orders(self) -> List[OrderResult]:
        """Get all pending orders."""
        if not self._connected:
            await self.connect()

        orders_data = await self._request(
            "GET",
            f"/users/current/accounts/{self.account_id}/orders",
        )

        orders = []
        for order in orders_data:
            side = OrderSide.BUY if "BUY" in order.get("type", "") else OrderSide.SELL

            order_type = OrderType.MARKET
            if "LIMIT" in order.get("type", ""):
                order_type = OrderType.LIMIT
            elif "STOP" in order.get("type", ""):
                order_type = OrderType.STOP

            orders.append(OrderResult(
                order_id=str(order.get("id")),
                symbol=order.get("symbol", ""),
                side=side,
                order_type=order_type,
                status=OrderStatus.PENDING,
                size=Decimal(str(order.get("volume", 0))),
                filled_size=Decimal("0"),
                price=Decimal(str(order.get("openPrice", 0))) if order.get("openPrice") else None,
            ))

        return orders

    async def get_price(self, symbol: str) -> Optional[Tick]:
        """Get current price for a symbol."""
        if not self._connected:
            await self.connect()

        try:
            price_data = await self._request(
                "GET",
                f"/users/current/accounts/{self.account_id}/symbols/{symbol}/current-price",
            )

            return Tick(
                symbol=symbol,
                bid=Decimal(str(price_data.get("bid", 0))),
                ask=Decimal(str(price_data.get("ask", 0))),
                timestamp=datetime.now(),
            )
        except Exception:
            return None

    async def stream_prices(
        self,
        symbols: List[str],
    ) -> AsyncIterator[Tick]:
        """
        Stream live prices.

        Note: MetaApi uses WebSocket for real-time prices.
        This implementation polls for simplicity.
        For production, use their WebSocket streaming API.
        """
        if not self._connected:
            await self.connect()

        while True:
            for symbol in symbols:
                try:
                    tick = await self.get_price(symbol)
                    if tick:
                        yield tick
                except Exception:
                    pass
            await asyncio.sleep(1)  # Poll every second

    async def get_symbols(self) -> List[Dict[str, Any]]:
        """Get available trading symbols."""
        if not self._connected:
            await self.connect()

        symbols = await self._request(
            "GET",
            f"/users/current/accounts/{self.account_id}/symbols",
        )

        return symbols

    async def get_candles(
        self,
        symbol: str,
        timeframe: str = "1h",
        count: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get historical candles.

        Timeframes: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1mn
        """
        if not self._connected:
            await self.connect()

        # Map timeframe to MetaApi format
        tf_map = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w",
        }
        mt_timeframe = tf_map.get(timeframe, "1h")

        candles = await self._request(
            "GET",
            f"/users/current/accounts/{self.account_id}/historical-market-data/symbols/{symbol}/timeframes/{mt_timeframe}/candles",
            params={"limit": count},
        )

        return candles
