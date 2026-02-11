"""
Alpha Vantage Integration

Provides market data, technical indicators, and fundamental data
from Alpha Vantage API.

Free tier: 25 requests/day
Premium tier: Unlimited requests
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

import httpx

from src.core.config import settings


class Interval(str, Enum):
    """Time intervals for data."""
    MIN_1 = "1min"
    MIN_5 = "5min"
    MIN_15 = "15min"
    MIN_30 = "30min"
    MIN_60 = "60min"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class OutputSize(str, Enum):
    """Output size for historical data."""
    COMPACT = "compact"  # Last 100 data points
    FULL = "full"  # Full history (20+ years)


@dataclass
class ForexQuote:
    """Real-time forex quote."""
    from_currency: str
    to_currency: str
    exchange_rate: Decimal
    bid_price: Decimal
    ask_price: Decimal
    timestamp: datetime


@dataclass
class OHLCV:
    """OHLCV candlestick data."""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int = 0


@dataclass
class TechnicalIndicator:
    """Technical indicator value."""
    timestamp: datetime
    value: float
    additional_values: dict[str, float] = None


@dataclass
class EconomicIndicator:
    """Economic indicator data."""
    name: str
    date: datetime
    value: float
    unit: str = ""


class AlphaVantageClient:
    """
    Alpha Vantage API Client

    Provides:
    - Real-time forex quotes
    - Historical forex data (intraday & daily)
    - Technical indicators (RSI, MACD, SMA, EMA, etc.)
    - Economic indicators (GDP, inflation, interest rates)
    - Global market status
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str | None = None):
        """Initialize Alpha Vantage client."""
        self.api_key = api_key or getattr(settings, 'ALPHA_VANTAGE_API_KEY', None)
        self._client: httpx.AsyncClient | None = None
        self._rate_limit_remaining = 25  # Free tier limit

    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)

    async def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        """Make API request with rate limiting."""
        await self._ensure_client()

        if not self.api_key:
            raise ValueError("Alpha Vantage API key not configured")

        params["apikey"] = self.api_key

        response = await self._client.get(self.BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()

        # Check for API errors
        if "Error Message" in data:
            raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
        if "Note" in data:
            raise ValueError(f"Rate limit reached: {data['Note']}")

        return data

    # ========== Forex Data ==========

    async def get_forex_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> ForexQuote:
        """
        Get real-time forex exchange rate.

        Args:
            from_currency: Base currency (e.g., "EUR")
            to_currency: Quote currency (e.g., "USD")

        Returns:
            ForexQuote with current rate
        """
        data = await self._request({
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": from_currency,
            "to_currency": to_currency,
        })

        rate_data = data.get("Realtime Currency Exchange Rate", {})

        return ForexQuote(
            from_currency=rate_data.get("1. From_Currency Code", from_currency),
            to_currency=rate_data.get("3. To_Currency Code", to_currency),
            exchange_rate=Decimal(rate_data.get("5. Exchange Rate", "0")),
            bid_price=Decimal(rate_data.get("8. Bid Price", "0")),
            ask_price=Decimal(rate_data.get("9. Ask Price", "0")),
            timestamp=datetime.fromisoformat(
                rate_data.get("6. Last Refreshed", datetime.now().isoformat())
            ),
        )

    async def get_forex_intraday(
        self,
        from_symbol: str,
        to_symbol: str,
        interval: Interval = Interval.MIN_5,
        outputsize: OutputSize = OutputSize.COMPACT,
    ) -> list[OHLCV]:
        """
        Get intraday forex data.

        Args:
            from_symbol: Base currency
            to_symbol: Quote currency
            interval: Time interval
            outputsize: compact (100 points) or full

        Returns:
            List of OHLCV candles
        """
        data = await self._request({
            "function": "FX_INTRADAY",
            "from_symbol": from_symbol,
            "to_symbol": to_symbol,
            "interval": interval.value,
            "outputsize": outputsize.value,
        })

        time_series_key = f"Time Series FX ({interval.value})"
        time_series = data.get(time_series_key, {})

        candles = []
        for timestamp_str, ohlc in time_series.items():
            candles.append(OHLCV(
                timestamp=datetime.fromisoformat(timestamp_str),
                open=Decimal(ohlc["1. open"]),
                high=Decimal(ohlc["2. high"]),
                low=Decimal(ohlc["3. low"]),
                close=Decimal(ohlc["4. close"]),
            ))

        return sorted(candles, key=lambda x: x.timestamp)

    async def get_forex_daily(
        self,
        from_symbol: str,
        to_symbol: str,
        outputsize: OutputSize = OutputSize.COMPACT,
    ) -> list[OHLCV]:
        """Get daily forex data."""
        data = await self._request({
            "function": "FX_DAILY",
            "from_symbol": from_symbol,
            "to_symbol": to_symbol,
            "outputsize": outputsize.value,
        })

        time_series = data.get("Time Series FX (Daily)", {})

        candles = []
        for timestamp_str, ohlc in time_series.items():
            candles.append(OHLCV(
                timestamp=datetime.fromisoformat(timestamp_str),
                open=Decimal(ohlc["1. open"]),
                high=Decimal(ohlc["2. high"]),
                low=Decimal(ohlc["3. low"]),
                close=Decimal(ohlc["4. close"]),
            ))

        return sorted(candles, key=lambda x: x.timestamp)

    # ========== Technical Indicators ==========

    async def get_rsi(
        self,
        symbol: str,
        interval: Interval = Interval.DAILY,
        time_period: int = 14,
        series_type: str = "close",
    ) -> list[TechnicalIndicator]:
        """Get RSI indicator values."""
        data = await self._request({
            "function": "RSI",
            "symbol": symbol,
            "interval": interval.value,
            "time_period": time_period,
            "series_type": series_type,
        })

        indicators = []
        for timestamp_str, values in data.get("Technical Analysis: RSI", {}).items():
            indicators.append(TechnicalIndicator(
                timestamp=datetime.fromisoformat(timestamp_str),
                value=float(values["RSI"]),
            ))

        return sorted(indicators, key=lambda x: x.timestamp)

    async def get_macd(
        self,
        symbol: str,
        interval: Interval = Interval.DAILY,
        series_type: str = "close",
        fastperiod: int = 12,
        slowperiod: int = 26,
        signalperiod: int = 9,
    ) -> list[TechnicalIndicator]:
        """Get MACD indicator values."""
        data = await self._request({
            "function": "MACD",
            "symbol": symbol,
            "interval": interval.value,
            "series_type": series_type,
            "fastperiod": fastperiod,
            "slowperiod": slowperiod,
            "signalperiod": signalperiod,
        })

        indicators = []
        for timestamp_str, values in data.get("Technical Analysis: MACD", {}).items():
            indicators.append(TechnicalIndicator(
                timestamp=datetime.fromisoformat(timestamp_str),
                value=float(values["MACD"]),
                additional_values={
                    "signal": float(values["MACD_Signal"]),
                    "histogram": float(values["MACD_Hist"]),
                },
            ))

        return sorted(indicators, key=lambda x: x.timestamp)

    async def get_sma(
        self,
        symbol: str,
        interval: Interval = Interval.DAILY,
        time_period: int = 20,
        series_type: str = "close",
    ) -> list[TechnicalIndicator]:
        """Get SMA indicator values."""
        data = await self._request({
            "function": "SMA",
            "symbol": symbol,
            "interval": interval.value,
            "time_period": time_period,
            "series_type": series_type,
        })

        indicators = []
        for timestamp_str, values in data.get("Technical Analysis: SMA", {}).items():
            indicators.append(TechnicalIndicator(
                timestamp=datetime.fromisoformat(timestamp_str),
                value=float(values["SMA"]),
            ))

        return sorted(indicators, key=lambda x: x.timestamp)

    async def get_ema(
        self,
        symbol: str,
        interval: Interval = Interval.DAILY,
        time_period: int = 20,
        series_type: str = "close",
    ) -> list[TechnicalIndicator]:
        """Get EMA indicator values."""
        data = await self._request({
            "function": "EMA",
            "symbol": symbol,
            "interval": interval.value,
            "time_period": time_period,
            "series_type": series_type,
        })

        indicators = []
        for timestamp_str, values in data.get("Technical Analysis: EMA", {}).items():
            indicators.append(TechnicalIndicator(
                timestamp=datetime.fromisoformat(timestamp_str),
                value=float(values["EMA"]),
            ))

        return sorted(indicators, key=lambda x: x.timestamp)

    async def get_bbands(
        self,
        symbol: str,
        interval: Interval = Interval.DAILY,
        time_period: int = 20,
        series_type: str = "close",
        nbdevup: int = 2,
        nbdevdn: int = 2,
    ) -> list[TechnicalIndicator]:
        """Get Bollinger Bands indicator values."""
        data = await self._request({
            "function": "BBANDS",
            "symbol": symbol,
            "interval": interval.value,
            "time_period": time_period,
            "series_type": series_type,
            "nbdevup": nbdevup,
            "nbdevdn": nbdevdn,
        })

        indicators = []
        for timestamp_str, values in data.get("Technical Analysis: BBANDS", {}).items():
            indicators.append(TechnicalIndicator(
                timestamp=datetime.fromisoformat(timestamp_str),
                value=float(values["Real Middle Band"]),
                additional_values={
                    "upper": float(values["Real Upper Band"]),
                    "lower": float(values["Real Lower Band"]),
                },
            ))

        return sorted(indicators, key=lambda x: x.timestamp)

    async def get_atr(
        self,
        symbol: str,
        interval: Interval = Interval.DAILY,
        time_period: int = 14,
    ) -> list[TechnicalIndicator]:
        """Get ATR indicator values."""
        data = await self._request({
            "function": "ATR",
            "symbol": symbol,
            "interval": interval.value,
            "time_period": time_period,
        })

        indicators = []
        for timestamp_str, values in data.get("Technical Analysis: ATR", {}).items():
            indicators.append(TechnicalIndicator(
                timestamp=datetime.fromisoformat(timestamp_str),
                value=float(values["ATR"]),
            ))

        return sorted(indicators, key=lambda x: x.timestamp)

    async def get_stoch(
        self,
        symbol: str,
        interval: Interval = Interval.DAILY,
        fastkperiod: int = 5,
        slowkperiod: int = 3,
        slowdperiod: int = 3,
    ) -> list[TechnicalIndicator]:
        """Get Stochastic oscillator values."""
        data = await self._request({
            "function": "STOCH",
            "symbol": symbol,
            "interval": interval.value,
            "fastkperiod": fastkperiod,
            "slowkperiod": slowkperiod,
            "slowdperiod": slowdperiod,
        })

        indicators = []
        for timestamp_str, values in data.get("Technical Analysis: STOCH", {}).items():
            indicators.append(TechnicalIndicator(
                timestamp=datetime.fromisoformat(timestamp_str),
                value=float(values["SlowK"]),
                additional_values={
                    "slowd": float(values["SlowD"]),
                },
            ))

        return sorted(indicators, key=lambda x: x.timestamp)

    # ========== Economic Indicators ==========

    async def get_real_gdp(self, interval: str = "annual") -> list[EconomicIndicator]:
        """Get US Real GDP data."""
        data = await self._request({
            "function": "REAL_GDP",
            "interval": interval,
        })

        indicators = []
        for item in data.get("data", []):
            indicators.append(EconomicIndicator(
                name="Real GDP",
                date=datetime.strptime(item["date"], "%Y-%m-%d"),
                value=float(item["value"]) if item["value"] != "." else 0,
                unit="billions of dollars",
            ))

        return indicators

    async def get_inflation(self) -> list[EconomicIndicator]:
        """Get US inflation data (CPI)."""
        data = await self._request({
            "function": "INFLATION",
        })

        indicators = []
        for item in data.get("data", []):
            indicators.append(EconomicIndicator(
                name="Inflation (CPI)",
                date=datetime.strptime(item["date"], "%Y-%m-%d"),
                value=float(item["value"]) if item["value"] != "." else 0,
                unit="percent",
            ))

        return indicators

    async def get_federal_funds_rate(self) -> list[EconomicIndicator]:
        """Get Federal Funds Rate data."""
        data = await self._request({
            "function": "FEDERAL_FUNDS_RATE",
            "interval": "monthly",
        })

        indicators = []
        for item in data.get("data", []):
            indicators.append(EconomicIndicator(
                name="Federal Funds Rate",
                date=datetime.strptime(item["date"], "%Y-%m-%d"),
                value=float(item["value"]) if item["value"] != "." else 0,
                unit="percent",
            ))

        return indicators

    async def get_unemployment(self) -> list[EconomicIndicator]:
        """Get unemployment rate data."""
        data = await self._request({
            "function": "UNEMPLOYMENT",
        })

        indicators = []
        for item in data.get("data", []):
            indicators.append(EconomicIndicator(
                name="Unemployment Rate",
                date=datetime.strptime(item["date"], "%Y-%m-%d"),
                value=float(item["value"]) if item["value"] != "." else 0,
                unit="percent",
            ))

        return indicators

    # ========== Market Status ==========

    async def get_market_status(self) -> dict[str, Any]:
        """Get global market status (open/closed)."""
        data = await self._request({
            "function": "MARKET_STATUS",
        })

        return data.get("markets", [])

    # ========== Utility Methods ==========

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
_alpha_vantage_client: AlphaVantageClient | None = None


def get_alpha_vantage_client() -> AlphaVantageClient:
    """Get or create Alpha Vantage client singleton."""
    global _alpha_vantage_client
    if _alpha_vantage_client is None:
        _alpha_vantage_client = AlphaVantageClient()
    return _alpha_vantage_client
