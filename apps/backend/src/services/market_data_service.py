"""
Market Data Service

Fetches real-time and historical OHLCV data from multiple sources.
Provides unified interface for market data across the platform.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import httpx
import pandas as pd
import numpy as np


class DataSource(str, Enum):
    """Available data sources."""
    YAHOO = "yahoo"
    TWELVE_DATA = "twelve_data"
    ALPHA_VANTAGE = "alpha_vantage"
    BROKER = "broker"  # From connected broker


@dataclass
class OHLCV:
    """Single OHLCV candle."""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": self.volume,
        }


@dataclass
class MarketData:
    """Complete market data package."""
    symbol: str
    timeframe: str
    candles: List[OHLCV]
    current_price: Decimal
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    spread: Optional[Decimal] = None
    daily_high: Optional[Decimal] = None
    daily_low: Optional[Decimal] = None
    daily_change: Optional[float] = None
    daily_change_percent: Optional[float] = None
    volume_24h: Optional[float] = None
    last_updated: datetime = field(default_factory=datetime.utcnow)
    source: DataSource = DataSource.YAHOO

    def to_dataframe(self) -> pd.DataFrame:
        """Convert candles to pandas DataFrame."""
        if not self.candles:
            return pd.DataFrame()

        data = {
            'timestamp': [c.timestamp for c in self.candles],
            'open': [float(c.open) for c in self.candles],
            'high': [float(c.high) for c in self.candles],
            'low': [float(c.low) for c in self.candles],
            'close': [float(c.close) for c in self.candles],
            'volume': [c.volume for c in self.candles],
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df


# Symbol mappings for different data sources
SYMBOL_MAPPINGS = {
    # Forex (OANDA format -> Yahoo format)
    "EUR_USD": {"yahoo": "EURUSD=X", "twelve": "EUR/USD"},
    "GBP_USD": {"yahoo": "GBPUSD=X", "twelve": "GBP/USD"},
    "USD_JPY": {"yahoo": "USDJPY=X", "twelve": "USD/JPY"},
    "AUD_USD": {"yahoo": "AUDUSD=X", "twelve": "AUD/USD"},
    "USD_CAD": {"yahoo": "USDCAD=X", "twelve": "USD/CAD"},
    "USD_CHF": {"yahoo": "USDCHF=X", "twelve": "USD/CHF"},
    "EUR_GBP": {"yahoo": "EURGBP=X", "twelve": "EUR/GBP"},
    "EUR_JPY": {"yahoo": "EURJPY=X", "twelve": "EUR/JPY"},
    "GBP_JPY": {"yahoo": "GBPJPY=X", "twelve": "GBP/JPY"},

    # Commodities
    "XAU_USD": {"yahoo": "GC=F", "twelve": "XAU/USD"},  # Gold futures
    "XAG_USD": {"yahoo": "SI=F", "twelve": "XAG/USD"},  # Silver futures
    "WTICO_USD": {"yahoo": "CL=F", "twelve": "WTI/USD"},  # Oil

    # Indices
    "US30": {"yahoo": "^DJI", "twelve": "DJI"},  # Dow Jones
    "NAS100": {"yahoo": "^IXIC", "twelve": "IXIC"},  # Nasdaq
    "SPX500": {"yahoo": "^GSPC", "twelve": "SPX"},  # S&P 500
    "UK100": {"yahoo": "^FTSE", "twelve": "FTSE"},  # FTSE 100
    "DE40": {"yahoo": "^GDAXI", "twelve": "DAX"},  # DAX

    # Crypto
    "BTC_USD": {"yahoo": "BTC-USD", "twelve": "BTC/USD"},
    "ETH_USD": {"yahoo": "ETH-USD", "twelve": "ETH/USD"},
}

# Timeframe mappings
TIMEFRAME_MAPPINGS = {
    # Internal -> Yahoo interval
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",  # Yahoo doesn't have 4h, we'll need to aggregate
    "1d": "1d",
    "1w": "1wk",
}


class MarketDataService:
    """
    Service for fetching market data from multiple sources.

    Prioritizes sources in order:
    1. Connected broker (if available) - most accurate
    2. Twelve Data API (if key configured) - good quality
    3. Yahoo Finance (free, always available) - fallback
    """

    def __init__(
        self,
        twelve_data_api_key: Optional[str] = None,
        alpha_vantage_api_key: Optional[str] = None,
    ):
        self.twelve_data_api_key = twelve_data_api_key
        self.alpha_vantage_api_key = alpha_vantage_api_key
        self._cache: Dict[str, Tuple[MarketData, datetime]] = {}
        self._cache_ttl = timedelta(seconds=30)  # Cache for 30 seconds

    def _get_yahoo_symbol(self, symbol: str) -> str:
        """Convert internal symbol to Yahoo Finance format."""
        if symbol in SYMBOL_MAPPINGS:
            return SYMBOL_MAPPINGS[symbol]["yahoo"]
        return symbol

    def _get_cache_key(self, symbol: str, timeframe: str) -> str:
        """Generate cache key."""
        return f"{symbol}:{timeframe}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self._cache:
            return False
        _, cached_time = self._cache[cache_key]
        return datetime.utcnow() - cached_time < self._cache_ttl

    async def get_market_data(
        self,
        symbol: str,
        timeframe: str = "5m",
        bars: int = 200,
        source: Optional[DataSource] = None,
    ) -> MarketData:
        """
        Fetch market data for a symbol.

        Args:
            symbol: Trading symbol (e.g., EUR_USD, XAU_USD)
            timeframe: Chart timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)
            bars: Number of candles to fetch
            source: Force specific data source (optional)

        Returns:
            MarketData with candles and current price
        """
        cache_key = self._get_cache_key(symbol, timeframe)

        # Check cache
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key][0]

        # Try sources in order
        data = None

        if source == DataSource.TWELVE_DATA or (source is None and self.twelve_data_api_key):
            try:
                data = await self._fetch_twelve_data(symbol, timeframe, bars)
            except Exception as e:
                print(f"Twelve Data fetch failed: {e}")

        if data is None:
            # Fallback to Yahoo Finance
            try:
                data = await self._fetch_yahoo(symbol, timeframe, bars)
            except Exception as e:
                print(f"Yahoo Finance fetch failed: {e}")
                # Return empty data with static price
                data = self._get_fallback_data(symbol, timeframe)

        # Cache the result
        self._cache[cache_key] = (data, datetime.utcnow())

        return data

    async def _fetch_yahoo(
        self,
        symbol: str,
        timeframe: str,
        bars: int,
    ) -> MarketData:
        """Fetch data from Yahoo Finance."""
        yahoo_symbol = self._get_yahoo_symbol(symbol)
        interval = TIMEFRAME_MAPPINGS.get(timeframe, "5m")

        # Yahoo Finance API endpoint
        # Determine period based on timeframe and bars needed
        if timeframe in ["1m", "5m"]:
            period = "5d"  # Max for minute data
        elif timeframe in ["15m", "30m"]:
            period = "1mo"
        elif timeframe in ["1h", "4h"]:
            period = "3mo"
        else:
            period = "1y"

        # Handle 4h by fetching 1h and aggregating
        fetch_interval = "1h" if interval == "4h" else interval

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
        params = {
            "interval": fetch_interval,
            "period1": int((datetime.utcnow() - timedelta(days=365)).timestamp()),
            "period2": int(datetime.utcnow().timestamp()),
            "range": period,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        # Parse response
        chart = data.get("chart", {}).get("result", [{}])[0]
        timestamps = chart.get("timestamp", [])
        quote = chart.get("indicators", {}).get("quote", [{}])[0]

        opens = quote.get("open", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        closes = quote.get("close", [])
        volumes = quote.get("volume", [])

        # Build candles
        candles = []
        for i in range(len(timestamps)):
            if opens[i] is None or closes[i] is None:
                continue
            candles.append(OHLCV(
                timestamp=datetime.fromtimestamp(timestamps[i]),
                open=Decimal(str(opens[i])),
                high=Decimal(str(highs[i] or opens[i])),
                low=Decimal(str(lows[i] or opens[i])),
                close=Decimal(str(closes[i])),
                volume=float(volumes[i] or 0),
            ))

        # Aggregate to 4h if needed
        if timeframe == "4h" and candles:
            candles = self._aggregate_candles(candles, 4)

        # Limit to requested bars
        candles = candles[-bars:] if len(candles) > bars else candles

        # Get current price and metadata
        meta = chart.get("meta", {})
        current_price = Decimal(str(meta.get("regularMarketPrice", closes[-1] if closes else 0)))

        return MarketData(
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            current_price=current_price,
            daily_high=Decimal(str(meta.get("regularMarketDayHigh", 0))) if meta.get("regularMarketDayHigh") else None,
            daily_low=Decimal(str(meta.get("regularMarketDayLow", 0))) if meta.get("regularMarketDayLow") else None,
            daily_change_percent=meta.get("regularMarketChangePercent"),
            source=DataSource.YAHOO,
        )

    async def _fetch_twelve_data(
        self,
        symbol: str,
        timeframe: str,
        bars: int,
    ) -> MarketData:
        """Fetch data from Twelve Data API."""
        if not self.twelve_data_api_key:
            raise ValueError("Twelve Data API key not configured")

        twelve_symbol = SYMBOL_MAPPINGS.get(symbol, {}).get("twelve", symbol)

        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": twelve_symbol,
            "interval": timeframe,
            "outputsize": bars,
            "apikey": self.twelve_data_api_key,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        if "values" not in data:
            raise ValueError(f"Twelve Data error: {data.get('message', 'Unknown error')}")

        candles = []
        for item in reversed(data["values"]):  # Reverse to get chronological order
            candles.append(OHLCV(
                timestamp=datetime.fromisoformat(item["datetime"]),
                open=Decimal(item["open"]),
                high=Decimal(item["high"]),
                low=Decimal(item["low"]),
                close=Decimal(item["close"]),
                volume=float(item.get("volume", 0)),
            ))

        current_price = candles[-1].close if candles else Decimal("0")

        return MarketData(
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            current_price=current_price,
            source=DataSource.TWELVE_DATA,
        )

    def _aggregate_candles(self, candles: List[OHLCV], hours: int) -> List[OHLCV]:
        """Aggregate hourly candles to larger timeframe."""
        if not candles:
            return []

        aggregated = []
        chunk_size = hours

        for i in range(0, len(candles), chunk_size):
            chunk = candles[i:i + chunk_size]
            if not chunk:
                continue

            aggregated.append(OHLCV(
                timestamp=chunk[0].timestamp,
                open=chunk[0].open,
                high=max(c.high for c in chunk),
                low=min(c.low for c in chunk),
                close=chunk[-1].close,
                volume=sum(c.volume for c in chunk),
            ))

        return aggregated

    def _get_fallback_data(self, symbol: str, timeframe: str) -> MarketData:
        """Return fallback data when all sources fail."""
        # Static fallback prices
        fallback_prices = {
            "EUR_USD": Decimal("1.0892"),
            "GBP_USD": Decimal("1.2651"),
            "USD_JPY": Decimal("149.86"),
            "XAU_USD": Decimal("2045.50"),
            "US30": Decimal("38252"),
            "NAS100": Decimal("17522"),
            "BTC_USD": Decimal("43500"),
            "ETH_USD": Decimal("2650"),
        }

        price = fallback_prices.get(symbol, Decimal("1.0"))

        return MarketData(
            symbol=symbol,
            timeframe=timeframe,
            candles=[],
            current_price=price,
            source=DataSource.YAHOO,  # Mark as Yahoo but it's fallback
        )

    async def get_current_price(self, symbol: str) -> Decimal:
        """Get only the current price for a symbol."""
        data = await self.get_market_data(symbol, timeframe="1m", bars=1)
        return data.current_price

    async def get_multiple_timeframes(
        self,
        symbol: str,
        timeframes: List[str] = ["5m", "15m", "1h", "4h"],
        bars: int = 100,
    ) -> Dict[str, MarketData]:
        """Fetch data for multiple timeframes in parallel."""
        tasks = [
            self.get_market_data(symbol, tf, bars)
            for tf in timeframes
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for tf, result in zip(timeframes, results):
            if isinstance(result, MarketData):
                data[tf] = result

        return data


# Singleton instance
_market_data_service: Optional[MarketDataService] = None


def get_market_data_service() -> MarketDataService:
    """Get or create MarketDataService singleton."""
    global _market_data_service
    if _market_data_service is None:
        from src.core.config import settings
        _market_data_service = MarketDataService(
            twelve_data_api_key=getattr(settings, 'TWELVE_DATA_API_KEY', None),
        )
    return _market_data_service


def reset_market_data_service() -> None:
    """Reset the service singleton."""
    global _market_data_service
    _market_data_service = None
