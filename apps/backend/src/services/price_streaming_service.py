"""
Price Streaming Service

Provides real-time price streaming from broker or fallback sources.
Integrates with WebSocket for live price updates to frontend.
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Set, Callable, Any
import random

from src.engines.trading.base_broker import BaseBroker, Tick
from src.engines.trading.broker_factory import get_broker


class PriceStreamingService:
    """
    Service for streaming real-time prices.

    Prioritizes:
    1. Connected broker (real-time)
    2. Simulated prices (for demo/testing)
    """

    def __init__(self):
        self._broker: Optional[BaseBroker] = None
        self._streaming = False
        self._subscribers: Dict[str, Set[Callable]] = {}  # symbol -> callbacks
        self._current_prices: Dict[str, Tick] = {}
        self._stream_task: Optional[asyncio.Task] = None

        # Base prices for simulation (when no broker)
        self._base_prices = {
            "EUR_USD": Decimal("1.0892"),
            "GBP_USD": Decimal("1.2651"),
            "USD_JPY": Decimal("149.86"),
            "AUD_USD": Decimal("0.6542"),
            "USD_CAD": Decimal("1.3654"),
            "XAU_USD": Decimal("2045.50"),
            "XAG_USD": Decimal("23.45"),
            "US30": Decimal("38252"),
            "NAS100": Decimal("17522"),
            "SPX500": Decimal("4925"),
            "BTC_USD": Decimal("43500"),
            "ETH_USD": Decimal("2650"),
        }

    async def initialize(self):
        """Initialize the service and try to connect to broker."""
        try:
            self._broker = await get_broker()
            if self._broker and self._broker.is_connected:
                print("✅ Price streaming: Using broker real-time data")
            else:
                print("⚠️ Price streaming: No broker connected, using simulated data")
                self._broker = None
        except Exception as e:
            print(f"⚠️ Price streaming: Could not get broker ({e}), using simulated data")
            self._broker = None

    @property
    def is_broker_connected(self) -> bool:
        """Check if broker is connected for real-time data."""
        return self._broker is not None and self._broker.is_connected

    @property
    def data_source(self) -> str:
        """Get current data source name."""
        if self.is_broker_connected:
            return self._broker.name
        return "simulated"

    def get_current_price(self, symbol: str) -> Optional[Tick]:
        """Get the latest cached price for a symbol."""
        return self._current_prices.get(symbol)

    def get_all_prices(self) -> Dict[str, Tick]:
        """Get all current prices."""
        return self._current_prices.copy()

    async def subscribe(self, symbol: str, callback: Callable[[Tick], Any]):
        """
        Subscribe to price updates for a symbol.

        Args:
            symbol: Trading symbol (e.g., EUR_USD)
            callback: Async function called with each Tick
        """
        if symbol not in self._subscribers:
            self._subscribers[symbol] = set()
        self._subscribers[symbol].add(callback)

        # Start streaming if not already
        if not self._streaming:
            await self.start_streaming()

    def unsubscribe(self, symbol: str, callback: Callable):
        """Unsubscribe from price updates."""
        if symbol in self._subscribers:
            self._subscribers[symbol].discard(callback)
            if not self._subscribers[symbol]:
                del self._subscribers[symbol]

    async def start_streaming(self):
        """Start the price streaming loop."""
        if self._streaming:
            return

        self._streaming = True

        if self.is_broker_connected:
            self._stream_task = asyncio.create_task(self._stream_from_broker())
        else:
            self._stream_task = asyncio.create_task(self._stream_simulated())

    async def stop_streaming(self):
        """Stop the price streaming loop."""
        self._streaming = False
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            self._stream_task = None

    async def _stream_from_broker(self):
        """Stream prices from connected broker."""
        while self._streaming and self.is_broker_connected:
            try:
                symbols = list(self._subscribers.keys())
                if not symbols:
                    await asyncio.sleep(0.5)
                    continue

                async for tick in self._broker.stream_prices(symbols):
                    if not self._streaming:
                        break

                    # Update cache
                    self._current_prices[tick.symbol] = tick

                    # Notify subscribers
                    await self._notify_subscribers(tick)

            except Exception as e:
                print(f"Broker streaming error: {e}")
                await asyncio.sleep(1)

    async def _stream_simulated(self):
        """Stream simulated prices when no broker is connected."""
        while self._streaming:
            try:
                symbols = list(self._subscribers.keys()) or list(self._base_prices.keys())

                for symbol in symbols:
                    base = self._base_prices.get(symbol, Decimal("1.0"))

                    # Simulate price movement (small random fluctuation)
                    # More realistic: smaller moves for forex, larger for indices/crypto
                    if symbol in ["US30", "NAS100", "SPX500"]:
                        fluctuation = Decimal(str(random.uniform(-2, 2)))
                    elif symbol in ["BTC_USD", "ETH_USD"]:
                        fluctuation = Decimal(str(random.uniform(-10, 10)))
                    elif symbol == "XAU_USD":
                        fluctuation = Decimal(str(random.uniform(-0.5, 0.5)))
                    else:
                        fluctuation = Decimal(str(random.uniform(-0.0003, 0.0003)))

                    # Update base price slightly for persistence
                    new_mid = base + fluctuation
                    self._base_prices[symbol] = new_mid

                    # Calculate spread based on instrument
                    if symbol in ["EUR_USD", "GBP_USD", "USD_JPY"]:
                        spread = Decimal("0.00010")  # 1 pip
                    elif symbol == "XAU_USD":
                        spread = Decimal("0.30")
                    elif symbol in ["US30", "NAS100", "SPX500"]:
                        spread = Decimal("1.0")
                    elif symbol in ["BTC_USD", "ETH_USD"]:
                        spread = Decimal("5.0")
                    else:
                        spread = Decimal("0.00015")

                    half_spread = spread / 2

                    tick = Tick(
                        symbol=symbol,
                        bid=new_mid - half_spread,
                        ask=new_mid + half_spread,
                        timestamp=datetime.utcnow(),
                    )

                    # Update cache
                    self._current_prices[symbol] = tick

                    # Notify subscribers
                    await self._notify_subscribers(tick)

                # Update every 500ms for smooth animation
                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Simulated streaming error: {e}")
                await asyncio.sleep(1)

    async def _notify_subscribers(self, tick: Tick):
        """Notify all subscribers of a price update."""
        if tick.symbol not in self._subscribers:
            return

        for callback in self._subscribers[tick.symbol]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(tick)
                else:
                    callback(tick)
            except Exception as e:
                print(f"Error in price callback: {e}")


# Singleton instance
_price_service: Optional[PriceStreamingService] = None


async def get_price_streaming_service() -> PriceStreamingService:
    """Get or create PriceStreamingService singleton."""
    global _price_service
    if _price_service is None:
        _price_service = PriceStreamingService()
        await _price_service.initialize()
    return _price_service


def reset_price_streaming_service():
    """Reset the service singleton."""
    global _price_service
    if _price_service:
        asyncio.create_task(_price_service.stop_streaming())
    _price_service = None
