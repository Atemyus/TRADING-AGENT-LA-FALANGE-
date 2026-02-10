"""
OANDA Broker Implementation

Full implementation of the BaseBroker interface for OANDA's v20 REST API.
Supports both practice (demo) and live trading environments.

OANDA API Documentation: https://developer.oanda.com/rest-live-v20/introduction/
"""

import json
from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal

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


class OANDABroker(BaseBroker):
    """
    OANDA broker implementation using the v20 REST API.

    Supports:
    - Forex pairs (70+)
    - CFD indices
    - Commodities
    - Bonds

    Features:
    - REST API for orders and account management
    - Streaming API for real-time prices
    - Practice (paper) and live trading
    """

    # API endpoints
    PRACTICE_API = "https://api-fxpractice.oanda.com"
    LIVE_API = "https://api-fxtrade.oanda.com"
    PRACTICE_STREAM = "https://stream-fxpractice.oanda.com"
    LIVE_STREAM = "https://stream-fxtrade.oanda.com"

    # Symbol mapping: App symbol -> OANDA symbol
    # OANDA uses specific naming conventions for CFD indices
    SYMBOL_MAP = {
        # ============ US INDICES ============
        'US30': 'US30_USD',          # Dow Jones Industrial Average
        'US500': 'SPX500_USD',       # S&P 500
        'NAS100': 'NAS100_USD',      # NASDAQ 100
        'US2000': 'US2000_USD',      # Russell 2000

        # ============ EUROPEAN INDICES ============
        'DE40': 'DE30_EUR',          # DAX (OANDA still uses DE30)
        'UK100': 'UK100_GBP',        # FTSE 100
        'FR40': 'FR40_EUR',          # CAC 40
        'EU50': 'EU50_EUR',          # Euro Stoxx 50
        'ES35': 'ES35_EUR',          # IBEX 35
        'IT40': 'IT40_EUR',          # FTSE MIB (if available, may vary)

        # ============ ASIAN INDICES ============
        'JP225': 'JP225_USD',        # Nikkei 225
        'HK50': 'HK33_HKD',          # Hang Seng (OANDA uses HK33)
        'AU200': 'AU200_AUD',        # ASX 200
        'CN50': 'CN50_USD',          # China A50

        # ============ METALS ============
        'XAU_USD': 'XAU_USD',        # Gold
        'XAG_USD': 'XAG_USD',        # Silver
        'XPT_USD': 'XPT_USD',        # Platinum
        'XPD_USD': 'XPD_USD',        # Palladium
        'XCU_USD': 'XCU_USD',        # Copper

        # ============ ENERGY / COMMODITIES ============
        'WTI_USD': 'WTICO_USD',      # WTI Crude Oil
        'BRENT_USD': 'BCO_USD',      # Brent Crude Oil
        'NATGAS_USD': 'NATGAS_USD',  # Natural Gas

        # ============ AGRICULTURAL (may not be available) ============
        'WHEAT_USD': 'WHEAT_USD',
        'CORN_USD': 'CORN_USD',
        'SOYBEAN_USD': 'SOYBN_USD',
        'COFFEE_USD': 'COFFEE_USD',
        'SUGAR_USD': 'SUGAR_USD',
        'COCOA_USD': 'COCOA_USD',
        'COTTON_USD': 'COTTON_USD',
    }

    # Reverse mapping for converting OANDA symbols back to app symbols
    REVERSE_SYMBOL_MAP = {v: k for k, v in SYMBOL_MAP.items()}

    def __init__(
        self,
        api_key: str | None = None,
        account_id: str | None = None,
        environment: str = "practice",
    ):
        """
        Initialize OANDA broker.

        Args:
            api_key: OANDA API key (from settings if not provided)
            account_id: OANDA account ID (from settings if not provided)
            environment: "practice" or "live"
        """
        super().__init__()

        self.api_key = api_key or settings.OANDA_API_KEY
        self.account_id = account_id or settings.OANDA_ACCOUNT_ID
        self.environment = environment or settings.OANDA_ENVIRONMENT

        if not self.api_key:
            raise ValueError("OANDA API key is required")
        if not self.account_id:
            raise ValueError("OANDA account ID is required")

        # Set API URLs based on environment
        if self.environment == "live":
            self.api_url = self.LIVE_API
            self.stream_url = self.LIVE_STREAM
        else:
            self.api_url = self.PRACTICE_API
            self.stream_url = self.PRACTICE_STREAM

        # HTTP client
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "OANDA"

    @property
    def supported_markets(self) -> list[str]:
        return ["forex", "indices", "commodities", "bonds"]

    def _get_headers(self) -> dict[str, str]:
        """Get authentication headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept-Datetime-Format": "RFC3339",
        }

    async def connect(self) -> None:
        """Establish connection to OANDA API."""
        if self._connected:
            return

        self._client = httpx.AsyncClient(
            headers=self._get_headers(),
            timeout=30.0,
        )

        # Test connection by fetching account
        try:
            response = await self._client.get(
                f"{self.api_url}/v3/accounts/{self.account_id}"
            )
            response.raise_for_status()
            self._connected = True
        except httpx.HTTPError as e:
            await self._client.aclose()
            self._client = None
            raise ConnectionError(f"Failed to connect to OANDA: {e}")

    async def disconnect(self) -> None:
        """Close connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """Make API request with error handling."""
        if not self._client:
            raise ConnectionError("Not connected to OANDA")

        url = f"{self.api_url}{endpoint}"

        try:
            if method == "GET":
                response = await self._client.get(url, params=params)
            elif method == "POST":
                response = await self._client.post(url, json=data)
            elif method == "PUT":
                response = await self._client.put(url, json=data)
            elif method == "DELETE":
                response = await self._client.delete(url)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            raise Exception(f"OANDA API error: {e.response.status_code} - {error_body}")

    # ==================== Account ====================

    async def get_account_info(self) -> AccountInfo:
        """Get current account information."""
        data = await self._request("GET", f"/v3/accounts/{self.account_id}")
        account = data["account"]

        return AccountInfo(
            account_id=account["id"],
            balance=Decimal(account["balance"]),
            equity=Decimal(account["NAV"]),
            margin_used=Decimal(account["marginUsed"]),
            margin_available=Decimal(account["marginAvailable"]),
            unrealized_pnl=Decimal(account["unrealizedPL"]),
            realized_pnl_today=Decimal(account.get("pl", "0")),
            currency=account["currency"],
            leverage=int(1 / float(account.get("marginRate", 0.05))),
            updated_at=datetime.fromisoformat(
                account["lastTransactionID"].replace("Z", "+00:00")
            ) if "lastTransactionID" in account else datetime.utcnow(),
        )

    # ==================== Instruments ====================

    async def get_instruments(self) -> list[Instrument]:
        """Get list of available trading instruments."""
        data = await self._request(
            "GET",
            f"/v3/accounts/{self.account_id}/instruments"
        )

        instruments = []
        for inst in data.get("instruments", []):
            # Determine instrument type
            inst_type = "forex"
            name = inst["name"]
            if "_" in name:
                if any(idx in name for idx in ["US30", "SPX500", "NAS100", "UK100", "DE30"]):
                    inst_type = "indices"
                elif any(cmd in name for cmd in ["XAU", "XAG", "BCO", "WTICO", "NATGAS"]):
                    inst_type = "commodities"

            instruments.append(Instrument(
                symbol=inst["name"],
                name=inst["displayName"],
                instrument_type=inst_type,
                pip_location=int(inst.get("pipLocation", -4)),
                min_size=Decimal(inst.get("minimumTradeSize", "1")),
                max_size=Decimal(inst.get("maximumOrderUnits", "100000000")),
                margin_rate=Decimal(inst.get("marginRate", "0.05")),
            ))

        return instruments

    # ==================== Orders ====================

    async def place_order(self, order: OrderRequest) -> OrderResult:
        """Place a new order."""
        # Build order data
        symbol = self.normalize_symbol(order.symbol)

        # Determine order units (negative for sell)
        units = str(order.size)
        if order.side == OrderSide.SELL:
            units = f"-{units}"

        order_data: dict = {
            "order": {
                "instrument": symbol,
                "units": units,
                "type": self._convert_order_type(order.order_type),
                "timeInForce": self._convert_tif(order.time_in_force),
                "positionFill": "DEFAULT",
            }
        }

        # Add price for limit orders
        if order.order_type == OrderType.LIMIT and order.price:
            order_data["order"]["price"] = str(order.price)

        # Add stop price for stop orders
        if order.order_type == OrderType.STOP and order.stop_price:
            order_data["order"]["price"] = str(order.stop_price)

        # Add stop loss
        if order.stop_loss:
            order_data["order"]["stopLossOnFill"] = {
                "price": str(order.stop_loss),
                "timeInForce": "GTC",
            }

        # Add take profit
        if order.take_profit:
            order_data["order"]["takeProfitOnFill"] = {
                "price": str(order.take_profit),
            }

        # Add client order ID
        if order.client_order_id:
            order_data["order"]["clientExtensions"] = {
                "id": order.client_order_id,
            }

        # Place order
        data = await self._request(
            "POST",
            f"/v3/accounts/{self.account_id}/orders",
            data=order_data,
        )

        # Parse response
        if "orderFillTransaction" in data:
            fill = data["orderFillTransaction"]
            return OrderResult(
                order_id=fill["orderID"],
                client_order_id=order.client_order_id,
                symbol=symbol,
                side=order.side,
                order_type=order.order_type,
                status=OrderStatus.FILLED,
                size=order.size,
                filled_size=Decimal(fill["units"].replace("-", "")),
                price=order.price,
                average_fill_price=Decimal(fill["price"]),
                commission=Decimal(fill.get("commission", "0")),
                created_at=datetime.fromisoformat(
                    fill["time"].replace("Z", "+00:00")
                ),
                filled_at=datetime.fromisoformat(
                    fill["time"].replace("Z", "+00:00")
                ),
            )
        elif "orderCreateTransaction" in data:
            create = data["orderCreateTransaction"]
            status = OrderStatus.PENDING
            if "orderCancelTransaction" in data:
                status = OrderStatus.CANCELLED
            elif "orderRejectTransaction" in data:
                status = OrderStatus.REJECTED

            return OrderResult(
                order_id=create["id"],
                client_order_id=order.client_order_id,
                symbol=symbol,
                side=order.side,
                order_type=order.order_type,
                status=status,
                size=order.size,
                filled_size=Decimal("0"),
                price=order.price,
                average_fill_price=None,
                created_at=datetime.fromisoformat(
                    create["time"].replace("Z", "+00:00")
                ),
                error_message=data.get("orderRejectTransaction", {}).get("rejectReason"),
            )
        else:
            raise Exception(f"Unexpected order response: {data}")

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        try:
            await self._request(
                "PUT",
                f"/v3/accounts/{self.account_id}/orders/{order_id}/cancel",
            )
            return True
        except Exception:
            return False

    async def get_order(self, order_id: str) -> OrderResult | None:
        """Get order by ID."""
        try:
            data = await self._request(
                "GET",
                f"/v3/accounts/{self.account_id}/orders/{order_id}",
            )
            order = data["order"]
            return self._parse_order(order)
        except Exception:
            return None

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        """Get all open/pending orders."""
        params = {}
        if symbol:
            params["instrument"] = self.normalize_symbol(symbol)

        data = await self._request(
            "GET",
            f"/v3/accounts/{self.account_id}/pendingOrders",
            params=params,
        )

        return [self._parse_order(o) for o in data.get("orders", [])]

    def _parse_order(self, order: dict) -> OrderResult:
        """Parse OANDA order response."""
        units = Decimal(order["units"])
        side = OrderSide.BUY if units > 0 else OrderSide.SELL

        return OrderResult(
            order_id=order["id"],
            client_order_id=order.get("clientExtensions", {}).get("id"),
            symbol=order["instrument"],
            side=side,
            order_type=self._parse_order_type(order["type"]),
            status=self._parse_order_status(order["state"]),
            size=abs(units),
            filled_size=Decimal(order.get("filledUnits", "0").replace("-", "")),
            price=Decimal(order["price"]) if "price" in order else None,
            average_fill_price=Decimal(order["averageFillPrice"]) if "averageFillPrice" in order else None,
            created_at=datetime.fromisoformat(
                order["createTime"].replace("Z", "+00:00")
            ),
        )

    # ==================== Positions ====================

    async def get_positions(self) -> list[Position]:
        """Get all open positions."""
        data = await self._request(
            "GET",
            f"/v3/accounts/{self.account_id}/openPositions",
        )

        positions = []
        for pos in data.get("positions", []):
            # OANDA returns separate long/short for each instrument
            if float(pos["long"]["units"]) != 0:
                positions.append(self._parse_position(pos, "long"))
            if float(pos["short"]["units"]) != 0:
                positions.append(self._parse_position(pos, "short"))

        return positions

    async def get_position(self, symbol: str) -> Position | None:
        """Get position for specific symbol."""
        symbol = self.normalize_symbol(symbol)

        try:
            data = await self._request(
                "GET",
                f"/v3/accounts/{self.account_id}/positions/{symbol}",
            )
            pos = data["position"]

            if float(pos["long"]["units"]) != 0:
                return self._parse_position(pos, "long")
            elif float(pos["short"]["units"]) != 0:
                return self._parse_position(pos, "short")
            return None
        except Exception:
            return None

    def _parse_position(self, pos: dict, side: str) -> Position:
        """Parse OANDA position response."""
        side_data = pos[side]
        units = Decimal(side_data["units"])

        return Position(
            position_id=f"{pos['instrument']}_{side}",
            symbol=pos["instrument"],
            side=PositionSide.LONG if side == "long" else PositionSide.SHORT,
            size=abs(units),
            entry_price=Decimal(side_data["averagePrice"]),
            current_price=Decimal(side_data["averagePrice"]),  # Will be updated
            unrealized_pnl=Decimal(side_data["unrealizedPL"]),
            margin_used=Decimal(pos.get("marginUsed", "0")),
        )

    async def close_position(
        self,
        symbol: str,
        size: Decimal | None = None,
    ) -> OrderResult:
        """Close a position."""
        symbol = self.normalize_symbol(symbol)

        # Get current position to determine direction
        position = await self.get_position(symbol)
        if not position:
            raise ValueError(f"No position found for {symbol}")

        # Build close request
        if size:
            if position.side == PositionSide.LONG:
                data = {"longUnits": str(size)}
            else:
                data = {"shortUnits": str(size)}
        else:
            if position.side == PositionSide.LONG:
                data = {"longUnits": "ALL"}
            else:
                data = {"shortUnits": "ALL"}

        response = await self._request(
            "PUT",
            f"/v3/accounts/{self.account_id}/positions/{symbol}/close",
            data=data,
        )

        # Parse response
        if "longOrderFillTransaction" in response:
            fill = response["longOrderFillTransaction"]
        elif "shortOrderFillTransaction" in response:
            fill = response["shortOrderFillTransaction"]
        else:
            raise Exception(f"Unexpected close response: {response}")

        return OrderResult(
            order_id=fill["orderID"],
            client_order_id=None,
            symbol=symbol,
            side=OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY,
            order_type=OrderType.MARKET,
            status=OrderStatus.FILLED,
            size=position.size if not size else size,
            filled_size=Decimal(fill["units"].replace("-", "")),
            price=None,
            average_fill_price=Decimal(fill["price"]),
            commission=Decimal(fill.get("commission", "0")),
            filled_at=datetime.fromisoformat(
                fill["time"].replace("Z", "+00:00")
            ),
        )

    async def modify_position(
        self,
        symbol: str,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
    ) -> bool:
        """Modify stop loss / take profit of existing position."""
        symbol = self.normalize_symbol(symbol)

        # Get open trades for this symbol
        data = await self._request(
            "GET",
            f"/v3/accounts/{self.account_id}/trades",
            params={"instrument": symbol, "state": "OPEN"},
        )

        trades = data.get("trades", [])
        if not trades:
            return False

        # Modify each trade
        for trade in trades:
            trade_id = trade["id"]
            update_data: dict = {}

            if stop_loss is not None:
                update_data["stopLoss"] = {"price": str(stop_loss), "timeInForce": "GTC"}
            if take_profit is not None:
                update_data["takeProfit"] = {"price": str(take_profit)}

            if update_data:
                await self._request(
                    "PUT",
                    f"/v3/accounts/{self.account_id}/trades/{trade_id}/orders",
                    data=update_data,
                )

        return True

    # ==================== Market Data ====================

    async def get_current_price(self, symbol: str) -> Tick:
        """Get current bid/ask price for symbol."""
        original_symbol = symbol
        oanda_symbol = self.normalize_symbol(symbol)

        data = await self._request(
            "GET",
            f"/v3/accounts/{self.account_id}/pricing",
            params={"instruments": oanda_symbol},
        )

        price = data["prices"][0]
        return Tick(
            symbol=original_symbol,  # Return with original app symbol
            bid=Decimal(price["bids"][0]["price"]),
            ask=Decimal(price["asks"][0]["price"]),
            timestamp=datetime.fromisoformat(
                price["time"].replace("Z", "+00:00")
            ),
        )

    async def get_prices(self, symbols: list[str]) -> dict[str, Tick]:
        """Get current prices for multiple symbols."""
        # Create mapping from OANDA symbol to original app symbol
        symbol_mapping = {}
        oanda_symbols = []
        for s in symbols:
            oanda_sym = self.normalize_symbol(s)
            oanda_symbols.append(oanda_sym)
            symbol_mapping[oanda_sym] = s  # Map OANDA symbol back to app symbol

        data = await self._request(
            "GET",
            f"/v3/accounts/{self.account_id}/pricing",
            params={"instruments": ",".join(oanda_symbols)},
        )

        result = {}
        for price in data["prices"]:
            oanda_sym = price["instrument"]
            # Use the original app symbol (e.g., US500 instead of SPX500_USD)
            app_symbol = symbol_mapping.get(oanda_sym, oanda_sym)

            result[app_symbol] = Tick(
                symbol=app_symbol,  # Use app symbol format
                bid=Decimal(price["bids"][0]["price"]),
                ask=Decimal(price["asks"][0]["price"]),
                timestamp=datetime.fromisoformat(
                    price["time"].replace("Z", "+00:00")
                ),
            )

        return result

    async def stream_prices(self, symbols: list[str]) -> AsyncIterator[Tick]:
        """Stream real-time prices using OANDA's streaming API."""
        # Create mapping from OANDA symbol to original app symbol
        symbol_mapping = {}
        oanda_symbols = []
        for s in symbols:
            oanda_sym = self.normalize_symbol(s)
            oanda_symbols.append(oanda_sym)
            symbol_mapping[oanda_sym] = s

        url = f"{self.stream_url}/v3/accounts/{self.account_id}/pricing/stream"
        params = {"instruments": ",".join(oanda_symbols)}

        async with httpx.AsyncClient(
            headers=self._get_headers(),
            timeout=None,  # Streaming connection
        ) as client:
            async with client.stream("GET", url, params=params) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        if data.get("type") == "PRICE":
                            oanda_sym = data["instrument"]
                            app_symbol = symbol_mapping.get(oanda_sym, oanda_sym)
                            yield Tick(
                                symbol=app_symbol,  # Use app symbol format
                                bid=Decimal(data["bids"][0]["price"]),
                                ask=Decimal(data["asks"][0]["price"]),
                                timestamp=datetime.fromisoformat(
                                    data["time"].replace("Z", "+00:00")
                                ),
                            )
                    except (json.JSONDecodeError, KeyError):
                        continue

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        count: int = 100,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> list[Candle]:
        """Get historical candle data."""
        symbol = self.normalize_symbol(symbol)
        granularity = self._convert_timeframe(timeframe)

        params: dict = {
            "granularity": granularity,
            "count": min(count, 5000),  # OANDA max
        }

        if from_time:
            params["from"] = from_time.isoformat() + "Z"
        if to_time:
            params["to"] = to_time.isoformat() + "Z"

        data = await self._request(
            "GET",
            f"/v3/instruments/{symbol}/candles",
            params=params,
        )

        candles = []
        for c in data.get("candles", []):
            if not c.get("complete", True):
                continue

            mid = c["mid"]
            candles.append(Candle(
                symbol=symbol,
                timestamp=datetime.fromisoformat(
                    c["time"].replace("Z", "+00:00")
                ),
                open=Decimal(mid["o"]),
                high=Decimal(mid["h"]),
                low=Decimal(mid["l"]),
                close=Decimal(mid["c"]),
                volume=Decimal(c.get("volume", 0)),
                timeframe=timeframe,
            ))

        return candles

    # ==================== Utility Methods ====================

    def normalize_symbol(self, symbol: str) -> str:
        """
        Convert symbol to OANDA format.

        Uses SYMBOL_MAP for known mappings (indices, commodities, etc.)
        Falls back to simple underscore replacement for forex pairs.
        """
        # First normalize the input
        normalized = symbol.replace("/", "_").upper()

        # Check if we have a specific mapping for this symbol
        if normalized in self.SYMBOL_MAP:
            return self.SYMBOL_MAP[normalized]

        # Default: return as-is (forex pairs like EUR_USD work directly)
        return normalized

    def denormalize_symbol(self, symbol: str) -> str:
        """
        Convert OANDA symbol to app format.

        Uses REVERSE_SYMBOL_MAP for known mappings.
        """
        # Check reverse mapping first
        if symbol in self.REVERSE_SYMBOL_MAP:
            return self.REVERSE_SYMBOL_MAP[symbol]

        # Default: return as-is
        return symbol

    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert order type to OANDA format."""
        mapping = {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.STOP: "STOP",
            OrderType.STOP_LIMIT: "STOP",
        }
        return mapping.get(order_type, "MARKET")

    def _parse_order_type(self, oanda_type: str) -> OrderType:
        """Parse OANDA order type."""
        mapping = {
            "MARKET": OrderType.MARKET,
            "LIMIT": OrderType.LIMIT,
            "STOP": OrderType.STOP,
            "MARKET_IF_TOUCHED": OrderType.LIMIT,
        }
        return mapping.get(oanda_type, OrderType.MARKET)

    def _parse_order_status(self, oanda_status: str) -> OrderStatus:
        """Parse OANDA order status."""
        mapping = {
            "PENDING": OrderStatus.PENDING,
            "FILLED": OrderStatus.FILLED,
            "TRIGGERED": OrderStatus.FILLED,
            "CANCELLED": OrderStatus.CANCELLED,
        }
        return mapping.get(oanda_status, OrderStatus.PENDING)

    def _convert_tif(self, tif: TimeInForce) -> str:
        """Convert time in force to OANDA format."""
        mapping = {
            TimeInForce.GTC: "GTC",
            TimeInForce.IOC: "IOC",
            TimeInForce.FOK: "FOK",
            TimeInForce.DAY: "GFD",
        }
        return mapping.get(tif, "GTC")

    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert timeframe to OANDA granularity."""
        mapping = {
            "M1": "M1",
            "1m": "M1",
            "M5": "M5",
            "5m": "M5",
            "M15": "M15",
            "15m": "M15",
            "M30": "M30",
            "30m": "M30",
            "H1": "H1",
            "1h": "H1",
            "H4": "H4",
            "4h": "H4",
            "D": "D",
            "1d": "D",
            "W": "W",
            "1w": "W",
            "M": "M",
        }
        return mapping.get(timeframe, "M15")
