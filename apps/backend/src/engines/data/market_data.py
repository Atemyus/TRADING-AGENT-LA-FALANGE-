"""
Market Data Service

Centralized service for fetching and caching market data.
Supports real-time streaming and historical data.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import AsyncIterator, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

import pandas as pd

from src.engines.trading.base_broker import BaseBroker, Tick, Candle
from src.engines.trading.broker_factory import get_broker


@dataclass
class PriceUpdate:
    """Real-time price update."""
    symbol: str
    bid: Decimal
    ask: Decimal
    mid: Decimal
    spread: Decimal
    timestamp: datetime
    change: Decimal = Decimal("0")
    change_percent: Decimal = Decimal("0")


@dataclass
class MarketDataCache:
    """Cache for market data."""
    prices: Dict[str, PriceUpdate] = field(default_factory=dict)
    candles: Dict[str, Dict[str, List[Candle]]] = field(default_factory=dict)
    last_update: datetime = field(default_factory=datetime.utcnow)


class MarketDataService:
    """
    Market data service for fetching and streaming prices.

    Features:
    - Real-time price streaming
    - Historical candle data
    - Price caching with TTL
    - Multiple timeframe support
    - Event-driven updates

    Usage:
        service = MarketDataService()
        await service.start()

        # Get current price
        price = await service.get_price("EUR_USD")

        # Stream prices
        async for tick in service.stream_prices(["EUR_USD", "GBP_USD"]):
            print(f"{tick.symbol}: {tick.mid}")

        # Get historical data
        candles = await service.get_candles("EUR_USD", "M5", count=100)
    """

    def __init__(self, broker: Optional[BaseBroker] = None):
        """
        Initialize market data service.

        Args:
            broker: Broker instance to use for data. If None, uses default.
        """
        self._broker = broker
        self._cache = MarketDataCache()
        self._subscribers: Dict[str, Set[Callable]] = {}
        self._streaming_task: Optional[asyncio.Task] = None
        self._streaming_symbols: Set[str] = set()
        self._running = False

    async def start(self, symbols: Optional[List[str]] = None) -> None:
        """
        Start the market data service.

        Args:
            symbols: Initial symbols to stream. Can add more later.
        """
        if self._running:
            return

        # Get broker if not provided
        if self._broker is None:
            self._broker = await get_broker()

        self._running = True

        # Start streaming if symbols provided
        if symbols:
            await self.subscribe(symbols)

    async def stop(self) -> None:
        """Stop the market data service."""
        self._running = False

        if self._streaming_task:
            self._streaming_task.cancel()
            try:
                await self._streaming_task
            except asyncio.CancelledError:
                pass
            self._streaming_task = None

        self._streaming_symbols.clear()
        self._subscribers.clear()

    async def subscribe(self, symbols: List[str]) -> None:
        """
        Subscribe to price updates for symbols.

        Args:
            symbols: List of symbols to subscribe to
        """
        new_symbols = set(symbols) - self._streaming_symbols
        if not new_symbols:
            return

        self._streaming_symbols.update(new_symbols)

        # Restart streaming with updated symbols
        if self._streaming_task:
            self._streaming_task.cancel()
            try:
                await self._streaming_task
            except asyncio.CancelledError:
                pass

        self._streaming_task = asyncio.create_task(
            self._stream_prices(list(self._streaming_symbols))
        )

    async def unsubscribe(self, symbols: List[str]) -> None:
        """
        Unsubscribe from price updates.

        Args:
            symbols: List of symbols to unsubscribe from
        """
        self._streaming_symbols -= set(symbols)

        for symbol in symbols:
            self._subscribers.pop(symbol, None)

    def add_price_callback(self, symbol: str, callback: Callable[[PriceUpdate], None]) -> None:
        """
        Add callback for price updates on a symbol.

        Args:
            symbol: Symbol to watch
            callback: Function to call on price update
        """
        if symbol not in self._subscribers:
            self._subscribers[symbol] = set()
        self._subscribers[symbol].add(callback)

    def remove_price_callback(self, symbol: str, callback: Callable) -> None:
        """Remove a price callback."""
        if symbol in self._subscribers:
            self._subscribers[symbol].discard(callback)

    async def _stream_prices(self, symbols: List[str]) -> None:
        """Internal price streaming loop."""
        if not self._broker:
            return

        try:
            async for tick in self._broker.stream_prices(symbols):
                if not self._running:
                    break

                # Calculate change from cached price
                prev_price = self._cache.prices.get(tick.symbol)
                change = Decimal("0")
                change_percent = Decimal("0")

                if prev_price:
                    change = tick.mid - prev_price.mid
                    if prev_price.mid != 0:
                        change_percent = (change / prev_price.mid) * 100

                # Create price update
                update = PriceUpdate(
                    symbol=tick.symbol,
                    bid=tick.bid,
                    ask=tick.ask,
                    mid=tick.mid,
                    spread=tick.spread,
                    timestamp=tick.timestamp,
                    change=change,
                    change_percent=change_percent,
                )

                # Update cache
                self._cache.prices[tick.symbol] = update
                self._cache.last_update = datetime.utcnow()

                # Notify subscribers
                if tick.symbol in self._subscribers:
                    for callback in self._subscribers[tick.symbol]:
                        try:
                            callback(update)
                        except Exception:
                            pass  # Don't let callback errors break streaming

        except asyncio.CancelledError:
            raise
        except Exception as e:
            # Log error and attempt reconnection
            print(f"Price streaming error: {e}")
            if self._running:
                await asyncio.sleep(5)
                self._streaming_task = asyncio.create_task(
                    self._stream_prices(symbols)
                )

    async def get_price(self, symbol: str, use_cache: bool = True) -> Optional[PriceUpdate]:
        """
        Get current price for a symbol.

        Args:
            symbol: Trading symbol
            use_cache: Whether to use cached price if available

        Returns:
            PriceUpdate or None if not available
        """
        # Check cache first
        if use_cache and symbol in self._cache.prices:
            cached = self._cache.prices[symbol]
            # Use cache if less than 5 seconds old
            if datetime.utcnow() - cached.timestamp < timedelta(seconds=5):
                return cached

        # Fetch from broker
        if not self._broker:
            self._broker = await get_broker()

        try:
            tick = await self._broker.get_current_price(symbol)
            update = PriceUpdate(
                symbol=tick.symbol,
                bid=tick.bid,
                ask=tick.ask,
                mid=tick.mid,
                spread=tick.spread,
                timestamp=tick.timestamp,
            )
            self._cache.prices[symbol] = update
            return update
        except Exception:
            return self._cache.prices.get(symbol)

    async def get_prices(self, symbols: List[str]) -> Dict[str, PriceUpdate]:
        """
        Get current prices for multiple symbols.

        Args:
            symbols: List of trading symbols

        Returns:
            Dictionary of symbol -> PriceUpdate
        """
        if not self._broker:
            self._broker = await get_broker()

        try:
            ticks = await self._broker.get_prices(symbols)
            result = {}

            for symbol, tick in ticks.items():
                update = PriceUpdate(
                    symbol=tick.symbol,
                    bid=tick.bid,
                    ask=tick.ask,
                    mid=tick.mid,
                    spread=tick.spread,
                    timestamp=tick.timestamp,
                )
                self._cache.prices[symbol] = update
                result[symbol] = update

            return result
        except Exception:
            return {s: self._cache.prices[s] for s in symbols if s in self._cache.prices}

    async def stream_prices(self, symbols: List[str]) -> AsyncIterator[PriceUpdate]:
        """
        Stream real-time prices.

        Args:
            symbols: Symbols to stream

        Yields:
            PriceUpdate objects as prices change
        """
        if not self._broker:
            self._broker = await get_broker()

        async for tick in self._broker.stream_prices(symbols):
            prev_price = self._cache.prices.get(tick.symbol)
            change = Decimal("0")
            change_percent = Decimal("0")

            if prev_price:
                change = tick.mid - prev_price.mid
                if prev_price.mid != 0:
                    change_percent = (change / prev_price.mid) * 100

            update = PriceUpdate(
                symbol=tick.symbol,
                bid=tick.bid,
                ask=tick.ask,
                mid=tick.mid,
                spread=tick.spread,
                timestamp=tick.timestamp,
                change=change,
                change_percent=change_percent,
            )

            self._cache.prices[tick.symbol] = update
            yield update

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        count: int = 100,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> List[Candle]:
        """
        Get historical candle data.

        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe (M1, M5, M15, H1, H4, D)
            count: Number of candles
            from_time: Start time
            to_time: End time
            use_cache: Whether to use cached data

        Returns:
            List of Candle objects
        """
        if not self._broker:
            self._broker = await get_broker()

        cache_key = f"{symbol}_{timeframe}"

        # Check cache
        if use_cache and cache_key in self._cache.candles:
            cached = self._cache.candles[cache_key]
            if len(cached) >= count:
                return cached[-count:]

        # Fetch from broker
        candles = await self._broker.get_candles(
            symbol=symbol,
            timeframe=timeframe,
            count=count,
            from_time=from_time,
            to_time=to_time,
        )

        # Update cache
        if symbol not in self._cache.candles:
            self._cache.candles[symbol] = {}
        self._cache.candles[symbol][timeframe] = candles

        return candles

    async def get_candles_df(
        self,
        symbol: str,
        timeframe: str,
        count: int = 100,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Get historical candle data as DataFrame.

        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            count: Number of candles
            from_time: Start time
            to_time: End time

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        candles = await self.get_candles(
            symbol=symbol,
            timeframe=timeframe,
            count=count,
            from_time=from_time,
            to_time=to_time,
        )

        if not candles:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        data = [
            {
                "timestamp": c.timestamp,
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": float(c.volume),
            }
            for c in candles
        ]

        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df


# Global instance
_market_data_service: Optional[MarketDataService] = None


async def get_market_data_service() -> MarketDataService:
    """Get the global market data service instance."""
    global _market_data_service

    if _market_data_service is None:
        _market_data_service = MarketDataService()
        await _market_data_service.start()

    return _market_data_service
