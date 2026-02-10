"""
Chart Vision Service - Generates chart images for AI visual analysis.

This service creates candlestick charts that are sent to vision-capable AI models
(GPT-4V, Claude Vision, Gemini Vision) for pattern recognition and analysis.
"""

import base64
import io
from datetime import datetime, timedelta
from typing import Any

# Optional imports for chart generation
HAS_MPLFINANCE = False
pd = None
np = None
mpf = None

try:
    import mplfinance as mpf
    import numpy as np
    import pandas as pd
    HAS_MPLFINANCE = True
except ImportError:
    pass



class ChartVisionService:
    """Generates chart images for multi-timeframe visual AI analysis."""

    # Timeframe configurations
    TIMEFRAMES = {
        "1m": {"minutes": 1, "candles": 100, "label": "1 Minute"},
        "5m": {"minutes": 5, "candles": 100, "label": "5 Minutes"},
        "15m": {"minutes": 15, "candles": 100, "label": "15 Minutes"},
        "1H": {"minutes": 60, "candles": 100, "label": "1 Hour"},
        "4H": {"minutes": 240, "candles": 100, "label": "4 Hours"},
        "1D": {"minutes": 1440, "candles": 100, "label": "Daily"},
    }

    # Dark theme for charts (matches TradingView dark mode)
    CHART_STYLE = {
        "base_mpl_style": "dark_background",
        "marketcolors": {
            "candle": {"up": "#22c55e", "down": "#ef4444"},
            "edge": {"up": "#22c55e", "down": "#ef4444"},
            "wick": {"up": "#22c55e", "down": "#ef4444"},
            "ohlc": {"up": "#22c55e", "down": "#ef4444"},
            "volume": {"up": "#22c55e80", "down": "#ef444480"},
            "vcedge": {"up": "#22c55e", "down": "#ef4444"},
            "vcdopcod": False,
            "alpha": 1.0,
        },
        "mavcolors": ["#6366f1", "#f59e0b", "#ec4899"],
        "facecolor": "#0f172a",
        "edgecolor": "#0f172a",
        "figcolor": "#0f172a",
        "gridcolor": "#1e293b",
        "gridstyle": "-",
        "y_on_right": True,
        "rc": {
            "axes.labelcolor": "#94a3b8",
            "axes.edgecolor": "#1e293b",
            "xtick.color": "#94a3b8",
            "ytick.color": "#94a3b8",
            "font.size": 10,
        },
    }

    def __init__(self):
        if not HAS_MPLFINANCE:
            raise ImportError(
                "mplfinance is required for chart generation. "
                "Install with: pip install mplfinance"
            )
        self._style = mpf.make_mpf_style(**self.CHART_STYLE)

    async def generate_chart_image(
        self,
        symbol: str,
        timeframe: str,
        ohlcv_data: Any | None = None,  # pd.DataFrame when available
        include_indicators: bool = True,
        width: int = 1200,
        height: int = 800,
    ) -> str:
        """
        Generate a chart image and return as base64 string.

        Args:
            symbol: Trading symbol (e.g., "EUR/USD")
            timeframe: Timeframe string (e.g., "1H", "4H")
            ohlcv_data: Optional DataFrame with OHLCV data. If None, generates demo data.
            include_indicators: Whether to include technical indicators
            width: Image width in pixels
            height: Image height in pixels

        Returns:
            Base64-encoded PNG image string
        """
        # Get or generate data
        if ohlcv_data is None:
            ohlcv_data = self._generate_demo_data(symbol, timeframe)

        # Prepare additional plots (indicators)
        addplots = []
        if include_indicators:
            addplots = self._calculate_indicators(ohlcv_data)

        # Create figure
        fig_ratio = (width / 100, height / 100)

        buf = io.BytesIO()

        # Generate chart
        mpf.plot(
            ohlcv_data,
            type="candle",
            style=self._style,
            volume=True,
            addplot=addplots if addplots else None,
            title=f"\n{symbol} - {self.TIMEFRAMES.get(timeframe, {}).get('label', timeframe)}",
            figsize=fig_ratio,
            savefig=dict(fname=buf, format="png", dpi=100, bbox_inches="tight"),
            warn_too_much_data=1000,
        )

        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()

        return image_base64

    async def generate_multi_timeframe_charts(
        self,
        symbol: str,
        timeframes: list[str] = ["15m", "1H", "4H"],
        ohlcv_data_map: dict[str, Any] | None = None,  # Dict[str, pd.DataFrame]
    ) -> dict[str, str]:
        """
        Generate charts for multiple timeframes.

        Args:
            symbol: Trading symbol
            timeframes: List of timeframes to generate
            ohlcv_data_map: Optional dict mapping timeframe to OHLCV data

        Returns:
            Dict mapping timeframe to base64 image string
        """
        charts = {}

        for tf in timeframes:
            data = ohlcv_data_map.get(tf) if ohlcv_data_map else None
            charts[tf] = await self.generate_chart_image(
                symbol=symbol,
                timeframe=tf,
                ohlcv_data=data,
            )

        return charts

    def _generate_demo_data(self, symbol: str, timeframe: str) -> Any:  # pd.DataFrame
        """Generate realistic demo OHLCV data for testing."""
        config = self.TIMEFRAMES.get(timeframe, {"minutes": 60, "candles": 100})
        num_candles = config["candles"]
        interval_minutes = config["minutes"]

        # Base prices for different symbols
        base_prices = {
            "EUR/USD": 1.0856,
            "GBP/USD": 1.2654,
            "USD/JPY": 149.85,
            "XAU/USD": 2048.5,
            "US30": 38450,
            "NAS100": 17250,
            "SPX500": 4925,
            "BTCUSD": 43500,
        }

        base_price = base_prices.get(symbol, 100)
        volatility = base_price * 0.002

        # Generate timestamps
        end_time = datetime.now()
        timestamps = [
            end_time - timedelta(minutes=interval_minutes * i)
            for i in range(num_candles - 1, -1, -1)
        ]

        # Generate price data with random walk
        np.random.seed(42)  # Reproducible for demo
        prices = [base_price]
        for i in range(1, num_candles):
            trend = np.sin(i / 20) * volatility * 0.5
            change = np.random.normal(0, volatility) + trend * 0.1
            prices.append(prices[-1] + change)

        # Generate OHLCV
        data = []
        for i, (ts, close) in enumerate(zip(timestamps, prices)):
            open_price = prices[i - 1] if i > 0 else close
            high = max(open_price, close) + abs(np.random.normal(0, volatility * 0.5))
            low = min(open_price, close) - abs(np.random.normal(0, volatility * 0.5))
            volume = np.random.randint(1000, 10000) * 100

            data.append({
                "Open": open_price,
                "High": high,
                "Low": low,
                "Close": close,
                "Volume": volume,
            })

        df = pd.DataFrame(data, index=pd.DatetimeIndex(timestamps))
        df.index.name = "Date"

        return df

    def _calculate_indicators(self, df: Any) -> list:  # df: pd.DataFrame
        """Calculate technical indicators for chart overlay."""
        addplots = []

        # EMA 20
        ema20 = df["Close"].ewm(span=20, adjust=False).mean()
        addplots.append(mpf.make_addplot(ema20, color="#6366f1", width=1.5))

        # EMA 50
        ema50 = df["Close"].ewm(span=50, adjust=False).mean()
        addplots.append(mpf.make_addplot(ema50, color="#f59e0b", width=1.5))

        # Bollinger Bands
        sma20 = df["Close"].rolling(window=20).mean()
        std20 = df["Close"].rolling(window=20).std()
        bb_upper = sma20 + (std20 * 2)
        bb_lower = sma20 - (std20 * 2)

        addplots.append(mpf.make_addplot(bb_upper, color="#94a3b8", width=0.8, linestyle="--"))
        addplots.append(mpf.make_addplot(bb_lower, color="#94a3b8", width=0.8, linestyle="--"))

        return addplots

    def create_vision_prompt(
        self,
        symbol: str,
        timeframes: list[str],
        additional_context: str | None = None,
    ) -> str:
        """
        Create a detailed prompt for vision AI analysis.

        Args:
            symbol: Trading symbol
            timeframes: List of timeframes being analyzed
            additional_context: Optional additional market context

        Returns:
            Formatted prompt string for vision AI
        """
        tf_labels = [self.TIMEFRAMES.get(tf, {}).get("label", tf) for tf in timeframes]

        prompt = f"""Analyze these {symbol} charts across multiple timeframes: {', '.join(tf_labels)}.

You are an expert technical analyst. Examine each chart carefully and provide:

## 1. TREND ANALYSIS (per timeframe)
- Overall trend direction (bullish/bearish/sideways)
- Trend strength (strong/moderate/weak)
- Key support and resistance levels visible

## 2. PATTERN RECOGNITION
- Identify any chart patterns (head & shoulders, double top/bottom, triangles, flags, etc.)
- Candlestick patterns (engulfing, doji, hammer, shooting star, etc.)
- Note the timeframe where each pattern appears

## 3. INDICATOR ANALYSIS
- EMA 20/50 relationship (golden cross, death cross, etc.)
- Bollinger Bands position (squeeze, expansion, price at bands)
- Volume analysis (increasing/decreasing, volume spikes)

## 4. MULTI-TIMEFRAME CONFLUENCE
- Do the timeframes align? (all bullish, mixed signals, etc.)
- Higher timeframe trend vs lower timeframe signals
- Key levels that appear on multiple timeframes

## 5. TRADING RECOMMENDATION
Based on your analysis, provide:
- **Direction**: LONG, SHORT, or HOLD
- **Confidence**: 0-100%
- **Entry Zone**: Suggested price range for entry
- **Stop Loss**: Specific price level with reasoning
- **Take Profit**: Target price(s) with reasoning
- **Risk/Reward Ratio**: Calculated R:R

## 6. KEY RISKS
- What could invalidate this analysis?
- Key levels to watch
- Upcoming events/sessions to consider

{f"Additional Context: {additional_context}" if additional_context else ""}

Be specific and reference what you see in the charts. Base your analysis purely on the visual chart data provided."""

        return prompt


# Singleton instance
_chart_vision_service: ChartVisionService | None = None


def get_chart_vision_service() -> ChartVisionService:
    """Get or create the chart vision service singleton."""
    global _chart_vision_service
    if _chart_vision_service is None:
        _chart_vision_service = ChartVisionService()
    return _chart_vision_service
