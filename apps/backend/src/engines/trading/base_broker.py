"""
Base Broker Abstraction Layer

This module defines the abstract interface that all broker implementations must follow.
This allows the trading engine to work with any broker (OANDA, IG, IB, Alpaca, etc.)
without changing the core logic.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class OrderSide(str, Enum):
    """Order direction."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionSide(str, Enum):
    """Position direction."""
    LONG = "long"
    SHORT = "short"


class TimeInForce(str, Enum):
    """Order time in force."""
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill
    DAY = "day"  # Day order


@dataclass
class AccountInfo:
    """Account information."""
    account_id: str
    balance: Decimal
    equity: Decimal
    margin_used: Decimal
    margin_available: Decimal
    unrealized_pnl: Decimal
    realized_pnl_today: Decimal
    currency: str = "USD"
    leverage: int = 1
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def margin_level(self) -> Decimal | None:
        """Calculate margin level percentage."""
        if self.margin_used == 0:
            return None
        return (self.equity / self.margin_used) * 100


@dataclass
class Position:
    """Open position."""
    position_id: str
    symbol: str
    side: PositionSide
    size: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    margin_used: Decimal
    leverage: int = 1
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    opened_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def pnl_percent(self) -> Decimal:
        """Calculate P&L percentage."""
        if self.entry_price == 0:
            return Decimal("0")
        if self.side == PositionSide.LONG:
            return ((self.current_price - self.entry_price) / self.entry_price) * 100
        else:
            return ((self.entry_price - self.current_price) / self.entry_price) * 100


@dataclass
class OrderRequest:
    """Order request to be sent to broker."""
    symbol: str
    side: OrderSide
    order_type: OrderType
    size: Decimal
    price: Decimal | None = None  # For limit orders
    stop_price: Decimal | None = None  # For stop orders
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    time_in_force: TimeInForce = TimeInForce.GTC
    leverage: int = 1
    client_order_id: str | None = None


@dataclass
class OrderResult:
    """Result of an order execution."""
    order_id: str
    client_order_id: str | None = None
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    status: OrderStatus = OrderStatus.PENDING
    size: Decimal = Decimal("0")
    filled_size: Decimal = Decimal("0")
    price: Decimal | None = None
    average_fill_price: Decimal | None = None
    commission: Decimal = Decimal("0")
    created_at: datetime = field(default_factory=datetime.utcnow)
    filled_at: datetime | None = None
    error_message: str | None = None

    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED

    @property
    def is_rejected(self) -> bool:
        return self.status == OrderStatus.REJECTED


@dataclass
class Tick:
    """Price tick data."""
    symbol: str
    bid: Decimal
    ask: Decimal
    timestamp: datetime

    @property
    def mid(self) -> Decimal:
        """Mid price."""
        return (self.bid + self.ask) / 2

    @property
    def spread(self) -> Decimal:
        """Bid-ask spread."""
        return self.ask - self.bid


@dataclass
class Candle:
    """OHLCV candle data."""
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    timeframe: str


@dataclass
class Instrument:
    """Trading instrument information."""
    symbol: str
    name: str
    instrument_type: str  # forex, index, commodity, stock
    base_currency: str | None = None
    quote_currency: str | None = None
    pip_location: int = -4  # e.g., -4 means 0.0001
    min_size: Decimal = Decimal("1")
    max_size: Decimal | None = None
    size_increment: Decimal = Decimal("1")
    margin_rate: Decimal = Decimal("0.05")  # 5% margin = 20x leverage
    trading_hours: str | None = None


class BaseBroker(ABC):
    """
    Abstract base class for all broker implementations.

    All broker-specific implementations must inherit from this class
    and implement all abstract methods.

    Example Usage:
        broker = OANDABroker(api_key="...", account_id="...")
        await broker.connect()

        account = await broker.get_account_info()
        print(f"Balance: {account.balance}")

        order = OrderRequest(
            symbol="EUR_USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            size=Decimal("10000"),
            stop_loss=Decimal("1.0900"),
        )
        result = await broker.place_order(order)
    """

    def __init__(self):
        self._connected = False
        self._instruments_cache: dict[str, Instrument] = {}

    @property
    def is_connected(self) -> bool:
        """Check if broker is connected."""
        return self._connected

    @property
    @abstractmethod
    def name(self) -> str:
        """Broker name identifier."""
        pass

    @property
    @abstractmethod
    def supported_markets(self) -> list[str]:
        """List of supported market types (forex, indices, commodities, stocks)."""
        pass

    # ==================== Connection ====================

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to broker API.
        Should set self._connected = True on success.
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection to broker API.
        Should set self._connected = False.
        """
        pass

    # ==================== Account ====================

    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """Get current account information."""
        pass

    # ==================== Instruments ====================

    @abstractmethod
    async def get_instruments(self) -> list[Instrument]:
        """Get list of available trading instruments."""
        pass

    async def get_instrument(self, symbol: str) -> Instrument | None:
        """Get specific instrument by symbol."""
        if not self._instruments_cache:
            instruments = await self.get_instruments()
            self._instruments_cache = {i.symbol: i for i in instruments}
        return self._instruments_cache.get(symbol)

    # ==================== Orders ====================

    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResult:
        """
        Place a new order.

        Args:
            order: Order request with all parameters

        Returns:
            OrderResult with execution details
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.

        Args:
            order_id: The order ID to cancel

        Returns:
            True if cancelled successfully
        """
        pass

    @abstractmethod
    async def get_order(self, order_id: str) -> OrderResult | None:
        """Get order by ID."""
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        """Get all open/pending orders."""
        pass

    # ==================== Positions ====================

    @abstractmethod
    async def get_positions(self) -> list[Position]:
        """Get all open positions."""
        pass

    @abstractmethod
    async def get_position(self, symbol: str) -> Position | None:
        """Get position for specific symbol."""
        pass

    @abstractmethod
    async def close_position(
        self,
        symbol: str,
        size: Decimal | None = None  # None = close all
    ) -> OrderResult:
        """
        Close a position.

        Args:
            symbol: Symbol to close
            size: Size to close (None = close entire position)

        Returns:
            OrderResult of the closing order
        """
        pass

    @abstractmethod
    async def modify_position(
        self,
        symbol: str,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
    ) -> bool:
        """
        Modify stop loss / take profit of existing position.

        Args:
            symbol: Symbol of position to modify
            stop_loss: New stop loss price (None = no change)
            take_profit: New take profit price (None = no change)

        Returns:
            True if modified successfully
        """
        pass

    # ==================== Market Data ====================

    @abstractmethod
    async def get_current_price(self, symbol: str) -> Tick:
        """Get current bid/ask price for symbol."""
        pass

    @abstractmethod
    async def get_prices(self, symbols: list[str]) -> dict[str, Tick]:
        """Get current prices for multiple symbols."""
        pass

    @abstractmethod
    async def stream_prices(self, symbols: list[str]) -> AsyncIterator[Tick]:
        """
        Stream real-time prices.

        Args:
            symbols: List of symbols to stream

        Yields:
            Tick objects as prices update
        """
        pass

    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        timeframe: str,  # e.g., "M1", "M5", "M15", "H1", "D"
        count: int = 100,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> list[Candle]:
        """
        Get historical candle data.

        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe (M1, M5, M15, H1, H4, D, W, M)
            count: Number of candles to retrieve
            from_time: Start time (optional)
            to_time: End time (optional)

        Returns:
            List of Candle objects
        """
        pass

    # ==================== Utility Methods ====================

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol format for this broker.
        Override in subclass if broker uses different format.

        Example: "EUR/USD" -> "EUR_USD" for OANDA
        """
        return symbol

    def denormalize_symbol(self, symbol: str) -> str:
        """
        Convert broker symbol format back to standard.
        Override in subclass.

        Example: "EUR_USD" -> "EUR/USD"
        """
        return symbol

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        return False
