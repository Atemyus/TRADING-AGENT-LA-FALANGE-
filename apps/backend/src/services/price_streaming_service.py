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
    2. Simulated prices (for demo/testing) - can be disabled
    """

    def __init__(self, disable_simulation: bool = False):
        """
        Initialize the price streaming service.

        Args:
            disable_simulation: If True, only real broker data will be used.
                               No simulated prices will be generated.
        """
        self._broker: Optional[BaseBroker] = None
        self._streaming = False
        self._initialized = False  # Flag to track if initialization is complete
        self._subscribers: Dict[str, Set[Callable]] = {}  # symbol -> callbacks
        self._current_prices: Dict[str, Tick] = {}
        self._stream_task: Optional[asyncio.Task] = None
        self._rate_limited = False  # Track if broker is rate limited
        self._failed_symbols: Set[str] = set()  # Symbols that failed to get from broker
        self._available_symbols: Set[str] = set()  # Symbols successfully fetched from broker
        self._disable_simulation = disable_simulation  # If True, no simulated data

        # Base prices for simulation (when no broker) - ALL 74 symbols
        self._base_prices = {
            # Forex - Major Pairs
            "EUR_USD": Decimal("1.0892"),
            "GBP_USD": Decimal("1.2651"),
            "USD_JPY": Decimal("149.86"),
            "USD_CHF": Decimal("0.8825"),
            "AUD_USD": Decimal("0.6542"),
            "USD_CAD": Decimal("1.3568"),
            "NZD_USD": Decimal("0.6125"),
            # Forex - Cross Pairs
            "EUR_GBP": Decimal("0.8610"),
            "EUR_JPY": Decimal("163.25"),
            "GBP_JPY": Decimal("189.65"),
            "EUR_CHF": Decimal("0.9612"),
            "EUR_AUD": Decimal("1.6652"),
            "EUR_CAD": Decimal("1.4785"),
            "GBP_CHF": Decimal("1.1162"),
            "GBP_AUD": Decimal("1.9335"),
            "AUD_JPY": Decimal("98.05"),
            "AUD_CAD": Decimal("0.8875"),
            "AUD_NZD": Decimal("1.0682"),
            "CAD_JPY": Decimal("110.45"),
            "NZD_JPY": Decimal("91.82"),
            "CHF_JPY": Decimal("169.85"),
            # Forex - Exotic Pairs
            "EUR_TRY": Decimal("35.25"),
            "USD_TRY": Decimal("32.35"),
            "USD_MXN": Decimal("17.15"),
            "USD_ZAR": Decimal("18.65"),
            "USD_SGD": Decimal("1.3425"),
            "USD_HKD": Decimal("7.8125"),
            "USD_NOK": Decimal("10.85"),
            "USD_SEK": Decimal("10.45"),
            "USD_DKK": Decimal("6.92"),
            "USD_PLN": Decimal("4.02"),
            # Metals
            "XAU_USD": Decimal("2045.50"),
            "XAG_USD": Decimal("23.45"),
            "XPT_USD": Decimal("985.50"),
            "XPD_USD": Decimal("1025.00"),
            "XCU_USD": Decimal("3.85"),
            # Commodities - Energy
            "WTI_USD": Decimal("76.50"),
            "BRENT_USD": Decimal("81.20"),
            "NATGAS_USD": Decimal("2.85"),
            # Commodities - Agricultural
            "WHEAT_USD": Decimal("585.25"),
            "CORN_USD": Decimal("452.50"),
            "SOYBEAN_USD": Decimal("1185.75"),
            "COFFEE_USD": Decimal("185.50"),
            "SUGAR_USD": Decimal("21.85"),
            "COCOA_USD": Decimal("4525.00"),
            "COTTON_USD": Decimal("82.50"),
            # Indices - US
            "US30": Decimal("38252"),
            "US500": Decimal("4925"),
            "NAS100": Decimal("17522"),
            "US2000": Decimal("2015.50"),
            # Indices - European
            "DE40": Decimal("17850"),
            "UK100": Decimal("7650"),
            "FR40": Decimal("7525"),
            "EU50": Decimal("4685"),
            "ES35": Decimal("10125"),
            "IT40": Decimal("32850"),
            # Indices - Asian
            "JP225": Decimal("38500"),
            "HK50": Decimal("16850"),
            "AU200": Decimal("7625"),
            "CN50": Decimal("12150"),
            # Indices - Other
            "VIX": Decimal("14.25"),
            # Futures - Index
            "ES1": Decimal("4928.50"),
            "NQ1": Decimal("17535.25"),
            "YM1": Decimal("38275"),
            "RTY1": Decimal("2018.50"),
            # Futures - Metal
            "GC1": Decimal("2048.50"),
            "SI1": Decimal("23.52"),
            # Futures - Energy
            "CL1": Decimal("76.85"),
            "NG1": Decimal("2.88"),
            # Futures - Currency
            "6E1": Decimal("1.0895"),
            "6B1": Decimal("1.2655"),
            "6J1": Decimal("0.006685"),
            # Futures - Bond
            "ZB1": Decimal("118.25"),
            "ZN1": Decimal("110.75"),
        }

    async def initialize(self):
        """Initialize the service and try to connect to broker."""
        try:
            print("[PriceStreaming] Initializing price streaming service...")
            self._broker = await get_broker()

            if self._broker:
                print(f"[PriceStreaming] Got broker: {self._broker.name}")
                print(f"[PriceStreaming] Broker connected: {self._broker.is_connected}")

                # If broker exists but not connected, try to connect
                if not self._broker.is_connected:
                    print("[PriceStreaming] Broker not connected, attempting to connect...")
                    await self._broker.connect()
                    print(f"[PriceStreaming] Broker connected after retry: {self._broker.is_connected}")

                if self._broker.is_connected:
                    print(f"✅ Price streaming: Using broker real-time data from {self._broker.name}")
                else:
                    print("⚠️ Price streaming: Broker exists but not connected, using simulated data")
                    self._broker = None
            else:
                print("⚠️ Price streaming: No broker instance, using simulated data")

        except Exception as e:
            print(f"⚠️ Price streaming: Could not get broker ({e}), using simulated data")
            import traceback
            traceback.print_exc()
            self._broker = None
        finally:
            self._initialized = True
            print(f"[PriceStreaming] Service initialized. Broker: {self._broker.name if self._broker else 'None'}, Connected: {self.is_broker_connected}")

    @property
    def is_broker_connected(self) -> bool:
        """Check if broker is connected for real-time data."""
        return self._broker is not None and self._broker.is_connected

    @property
    def data_source(self) -> str:
        """Get current data source name."""
        if self.is_broker_connected:
            return self._broker.name
        if self._disable_simulation:
            return "broker_only"
        return "simulated"

    @property
    def simulation_disabled(self) -> bool:
        """Check if simulation is disabled."""
        return self._disable_simulation

    @property
    def available_symbols(self) -> Set[str]:
        """Get symbols that are available from the broker (real prices)."""
        return self._available_symbols.copy()

    @property
    def failed_symbols(self) -> Set[str]:
        """Get symbols that failed to fetch from broker (use simulation)."""
        return self._failed_symbols.copy()

    def is_symbol_available(self, symbol: str) -> bool:
        """Check if a symbol is available from the broker."""
        return symbol in self._available_symbols

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
            print("[PriceStreaming] Already streaming, skipping start")
            return

        # Wait for initialization to complete before starting
        # This prevents race condition where streaming starts before broker connects
        max_wait = 10  # Maximum 10 seconds wait
        waited = 0
        while not self._initialized and waited < max_wait:
            print(f"[PriceStreaming] Waiting for initialization... ({waited}s)")
            await asyncio.sleep(0.5)
            waited += 0.5

        if not self._initialized:
            print("[PriceStreaming] WARNING: Initialization not complete after timeout, proceeding anyway")

        self._streaming = True

        print(f"[PriceStreaming] Starting streaming. Broker connected: {self.is_broker_connected}")
        print(f"[PriceStreaming] Data source: {self.data_source}")

        if self.is_broker_connected:
            print("[PriceStreaming] Starting BROKER price stream")
            self._stream_task = asyncio.create_task(self._stream_from_broker())
        else:
            # Always start simulated stream as fallback so UI has prices
            print("[PriceStreaming] Starting SIMULATED price stream (no broker connected)")
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
        """Stream prices from connected broker using polling for real-time sync."""
        print(f"[PriceStreaming] _stream_from_broker started for broker: {self._broker.name if self._broker else 'None'}")
        tick_count = 0
        base_poll_interval = 5.0  # Poll every 5 seconds to avoid rate limiting
        poll_interval = base_poll_interval
        # Use instance-level tracking for symbols
        self._failed_symbols = set()  # Reset on start
        self._available_symbols = set()  # Reset on start
        consecutive_errors = 0  # Track consecutive errors for backoff

        # Discover which symbols the broker actually supports
        supported_symbols = set()
        if hasattr(self._broker, 'get_supported_symbols'):
            supported_symbols = set(self._broker.get_supported_symbols())
            if supported_symbols:
                print(f"[PriceStreaming] Broker supports {len(supported_symbols)} symbols: {list(supported_symbols)[:10]}...")
            else:
                print("[PriceStreaming] No pre-mapped symbols yet, will discover during polling")

        while self._streaming and self.is_broker_connected:
            try:
                symbols = list(self._subscribers.keys())
                if not symbols:
                    await asyncio.sleep(poll_interval)
                    continue

                # Only poll symbols that broker supports (if we know which ones)
                # Otherwise try all symbols until we discover which ones work
                if supported_symbols:
                    broker_symbols = [s for s in symbols if s in supported_symbols and s not in self._failed_symbols]
                else:
                    broker_symbols = [s for s in symbols if s not in self._failed_symbols]
                simulated_symbols = [s for s in symbols if s in self._failed_symbols]

                # Get prices from broker for available symbols
                if broker_symbols and not self._rate_limited:
                    try:
                        # Log every 50 cycles (less frequent)
                        if tick_count % 50 == 0:
                            print(f"[PriceStreaming] Polling {len(broker_symbols)} symbols from broker (interval: {poll_interval}s)...")

                        prices = await self._broker.get_prices(broker_symbols)

                        # Reset backoff on success
                        consecutive_errors = 0
                        poll_interval = base_poll_interval

                        # Log result
                        if tick_count == 0 or tick_count % 50 == 0:
                            print(f"[PriceStreaming] Broker returned {len(prices)} prices")

                        # Track which symbols we got prices for
                        received_symbols = set(prices.keys())

                        for symbol, tick in prices.items():
                            tick_count += 1

                            # Log first few ticks and then every 100th
                            if tick_count <= 5 or tick_count % 100 == 0:
                                print(f"[PriceStreaming] Broker #{tick_count}: {tick.symbol} bid={tick.bid} ask={tick.ask}")

                            # Update cache
                            self._current_prices[tick.symbol] = tick

                            # Track available symbols (got real price from broker)
                            self._available_symbols.add(tick.symbol)

                            # Notify subscribers immediately
                            await self._notify_subscribers(tick)

                        # Mark symbols that broker didn't return as failed
                        for symbol in broker_symbols:
                            if symbol not in received_symbols:
                                if symbol not in self._failed_symbols:
                                    print(f"[PriceStreaming] Symbol {symbol} not available from broker, using simulation")
                                    self._failed_symbols.add(symbol)

                        # If broker returned NO prices at all, something is wrong
                        if len(prices) == 0 and len(broker_symbols) > 0:
                            print(f"[PriceStreaming] WARNING: Broker returned 0 prices for {len(broker_symbols)} symbols!")
                            consecutive_errors += 1
                            # Exponential backoff up to 30 seconds
                            poll_interval = min(base_poll_interval * (2 ** consecutive_errors), 30.0)

                    except Exception as poll_error:
                        error_str = str(poll_error)
                        consecutive_errors += 1

                        # Check if it's a rate limit error
                        if "rate limit" in error_str.lower() or "429" in error_str or "RateLimitError" in error_str:
                            print(f"[PriceStreaming] Rate limit detected! Switching to simulation mode for 5 minutes...")
                            self._rate_limited = True
                            # Schedule to re-enable broker after 5 minutes
                            asyncio.create_task(self._re_enable_broker_after_delay(300))
                        else:
                            print(f"[PriceStreaming] Broker polling error: {poll_error}")
                            # Exponential backoff up to 30 seconds
                            poll_interval = min(base_poll_interval * (2 ** consecutive_errors), 30.0)
                            print(f"[PriceStreaming] Backing off, next poll in {poll_interval}s")

                # Generate simulated prices for symbols not available from broker
                # Only if simulation is enabled
                if not self._disable_simulation:
                    symbols_to_simulate = simulated_symbols if not self._rate_limited else symbols
                    for symbol in symbols_to_simulate:
                        tick = self._generate_simulated_tick(symbol)
                        if tick:
                            self._current_prices[symbol] = tick
                            await self._notify_subscribers(tick)

                # Wait before next poll cycle
                await asyncio.sleep(poll_interval if not self._rate_limited else 1.0)

            except Exception as e:
                print(f"[PriceStreaming] Broker error: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(2)

    async def _re_enable_broker_after_delay(self, delay_seconds: int):
        """Re-enable broker polling after a delay."""
        print(f"[PriceStreaming] Will re-enable broker polling in {delay_seconds} seconds...")
        await asyncio.sleep(delay_seconds)
        self._rate_limited = False
        print("[PriceStreaming] Re-enabled broker polling")

    def _generate_simulated_tick(self, symbol: str) -> Optional[Tick]:
        """Generate a simulated tick for a single symbol."""
        base = self._base_prices.get(symbol)
        if base is None:
            return None

        fluctuation, spread = self._get_simulation_params(symbol, base)
        new_mid = base + fluctuation
        self._base_prices[symbol] = new_mid

        half_spread = spread / 2

        return Tick(
            symbol=symbol,
            bid=new_mid - half_spread,
            ask=new_mid + half_spread,
            timestamp=datetime.utcnow(),
        )

    async def _stream_simulated(self):
        """Stream simulated prices when no broker is connected."""
        print("[PriceStreaming] Starting simulated price stream for all symbols")

        while self._streaming:
            try:
                symbols = list(self._subscribers.keys()) or list(self._base_prices.keys())

                for symbol in symbols:
                    base = self._base_prices.get(symbol, Decimal("100.0"))

                    # Simulate price movement based on asset type
                    fluctuation, spread = self._get_simulation_params(symbol, base)

                    # Update base price slightly for persistence
                    new_mid = base + fluctuation
                    self._base_prices[symbol] = new_mid

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

    def _get_simulation_params(self, symbol: str, base: Decimal):
        """Get fluctuation and spread parameters based on symbol type."""
        # Forex pairs
        if any(x in symbol for x in ["EUR_", "GBP_", "USD_", "AUD_", "NZD_", "CAD_", "CHF_", "JPY"]):
            if "JPY" in symbol and "USD_JPY" not in symbol.replace("_", ""):
                # Cross JPY pairs (higher values)
                fluctuation = Decimal(str(random.uniform(-0.03, 0.03)))
                spread = Decimal("0.03")
            elif "TRY" in symbol or "MXN" in symbol or "ZAR" in symbol:
                # Exotic pairs (higher volatility)
                fluctuation = Decimal(str(random.uniform(-0.05, 0.05)))
                spread = Decimal("0.05")
            else:
                # Major and minor forex pairs
                fluctuation = Decimal(str(random.uniform(-0.0003, 0.0003)))
                spread = Decimal("0.00015")

        # Metals
        elif symbol in ["XAU_USD", "GC1"]:
            fluctuation = Decimal(str(random.uniform(-0.50, 0.50)))
            spread = Decimal("0.30")
        elif symbol in ["XAG_USD", "SI1"]:
            fluctuation = Decimal(str(random.uniform(-0.02, 0.02)))
            spread = Decimal("0.02")
        elif symbol in ["XPT_USD", "XPD_USD"]:
            fluctuation = Decimal(str(random.uniform(-1.0, 1.0)))
            spread = Decimal("1.0")
        elif symbol == "XCU_USD":
            fluctuation = Decimal(str(random.uniform(-0.005, 0.005)))
            spread = Decimal("0.01")

        # Commodities - Energy
        elif symbol in ["WTI_USD", "BRENT_USD", "CL1"]:
            fluctuation = Decimal(str(random.uniform(-0.05, 0.05)))
            spread = Decimal("0.03")
        elif symbol in ["NATGAS_USD", "NG1"]:
            fluctuation = Decimal(str(random.uniform(-0.005, 0.005)))
            spread = Decimal("0.005")

        # Commodities - Agricultural
        elif symbol in ["WHEAT_USD", "CORN_USD", "SOYBEAN_USD"]:
            fluctuation = Decimal(str(random.uniform(-0.50, 0.50)))
            spread = Decimal("0.25")
        elif symbol in ["COFFEE_USD", "SUGAR_USD", "COCOA_USD", "COTTON_USD"]:
            fluctuation = Decimal(str(random.uniform(-0.10, 0.10)))
            spread = Decimal("0.10")

        # Indices - US
        elif symbol in ["US30", "YM1"]:
            fluctuation = Decimal(str(random.uniform(-3.0, 3.0)))
            spread = Decimal("2.0")
        elif symbol in ["US500", "ES1"]:
            fluctuation = Decimal(str(random.uniform(-0.50, 0.50)))
            spread = Decimal("0.25")
        elif symbol in ["NAS100", "NQ1"]:
            fluctuation = Decimal(str(random.uniform(-2.0, 2.0)))
            spread = Decimal("1.0")
        elif symbol in ["US2000", "RTY1"]:
            fluctuation = Decimal(str(random.uniform(-0.20, 0.20)))
            spread = Decimal("0.10")

        # Indices - European
        elif symbol in ["DE40", "UK100", "FR40", "EU50", "ES35", "IT40"]:
            fluctuation = Decimal(str(random.uniform(-1.0, 1.0)))
            spread = Decimal("1.0")

        # Indices - Asian
        elif symbol == "JP225":
            fluctuation = Decimal(str(random.uniform(-5.0, 5.0)))
            spread = Decimal("5.0")
        elif symbol in ["HK50", "AU200", "CN50"]:
            fluctuation = Decimal(str(random.uniform(-1.0, 1.0)))
            spread = Decimal("1.0")

        # VIX
        elif symbol == "VIX":
            fluctuation = Decimal(str(random.uniform(-0.05, 0.05)))
            spread = Decimal("0.05")

        # Futures - Currency
        elif symbol in ["6E1", "6B1"]:
            fluctuation = Decimal(str(random.uniform(-0.0003, 0.0003)))
            spread = Decimal("0.00015")
        elif symbol == "6J1":
            fluctuation = Decimal(str(random.uniform(-0.000003, 0.000003)))
            spread = Decimal("0.000005")

        # Futures - Bonds
        elif symbol in ["ZB1", "ZN1"]:
            fluctuation = Decimal(str(random.uniform(-0.03, 0.03)))
            spread = Decimal("0.03")

        # Default fallback
        else:
            # Percentage-based fluctuation for unknown symbols
            pct = Decimal(str(random.uniform(-0.0001, 0.0001)))
            fluctuation = base * pct
            spread = base * Decimal("0.0002")

        return fluctuation, spread

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
_init_lock: asyncio.Lock = None  # Lock to prevent race condition during initialization
_init_complete: asyncio.Event = None  # Event to signal initialization is complete


async def get_price_streaming_service() -> PriceStreamingService:
    """
    Get or create PriceStreamingService singleton.

    Uses a lock to prevent race conditions where streaming starts
    before broker initialization completes.
    """
    global _price_service, _init_lock, _init_complete

    # Create lock and event on first call (must be in async context)
    if _init_lock is None:
        _init_lock = asyncio.Lock()
    if _init_complete is None:
        _init_complete = asyncio.Event()

    # Acquire lock to ensure only one initialization happens
    async with _init_lock:
        if _price_service is None:
            import os
            # Disable simulation by default - only use real broker data
            # Set ENABLE_PRICE_SIMULATION=true to enable simulated prices
            disable_simulation = os.getenv("ENABLE_PRICE_SIMULATION", "false").lower() != "true"
            print(f"[PriceStreaming] Creating new PriceStreamingService instance (simulation {'disabled' if disable_simulation else 'enabled'})...")
            _price_service = PriceStreamingService(disable_simulation=disable_simulation)
            await _price_service.initialize()
            _init_complete.set()  # Signal that initialization is complete
            print(f"[PriceStreaming] Initialization complete. Broker connected: {_price_service.is_broker_connected}")

    # Wait for initialization to complete (in case we didn't hold the lock)
    await _init_complete.wait()

    return _price_service


def reset_price_streaming_service():
    """Reset the service singleton."""
    global _price_service, _init_lock, _init_complete
    if _price_service:
        asyncio.create_task(_price_service.stop_streaming())
    _price_service = None
    _init_lock = None
    _init_complete = None
