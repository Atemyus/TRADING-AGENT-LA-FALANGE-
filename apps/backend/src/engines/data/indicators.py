"""
Technical Indicators Module

Comprehensive technical analysis indicators optimized for intraday/scalping.
Uses pandas and numpy for efficient calculations.

Indicators included:
- Trend: EMA, SMA, VWAP, Supertrend
- Momentum: RSI, MACD, Stochastic, Stochastic RSI
- Volatility: ATR, Bollinger Bands, Keltner Channels
- Support/Resistance: Pivot Points, Fibonacci
- Volume: OBV, Volume Profile, VWAP
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class IndicatorResult:
    """Result of indicator calculation."""
    name: str
    value: float
    signal: str  # "bullish", "bearish", "neutral"
    strength: float  # 0-100
    details: Dict = None


@dataclass
class AnalysisResult:
    """Complete technical analysis result."""
    symbol: str
    timeframe: str
    timestamp: str
    trend: str  # "bullish", "bearish", "neutral"
    trend_strength: float  # 0-100
    indicators: List[IndicatorResult]
    support_levels: List[float]
    resistance_levels: List[float]
    recommendation: str
    confidence: float


class TechnicalIndicators:
    """
    Technical analysis calculator.

    Usage:
        indicators = TechnicalIndicators(df)  # df with OHLCV data

        # Get individual indicators
        rsi = indicators.rsi()
        macd = indicators.macd()

        # Get full analysis
        analysis = indicators.analyze()
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with OHLCV DataFrame.

        Args:
            df: DataFrame with columns: open, high, low, close, volume
                Index should be datetime
        """
        self.df = df.copy()

        # Ensure column names are lowercase
        self.df.columns = self.df.columns.str.lower()

        # Validate required columns
        required = ["open", "high", "low", "close"]
        for col in required:
            if col not in self.df.columns:
                raise ValueError(f"Missing required column: {col}")

        # Add volume if missing
        if "volume" not in self.df.columns:
            self.df["volume"] = 0

    # ==================== Trend Indicators ====================

    def sma(self, period: int = 20, column: str = "close") -> pd.Series:
        """Simple Moving Average."""
        return self.df[column].rolling(window=period).mean()

    def ema(self, period: int = 20, column: str = "close") -> pd.Series:
        """Exponential Moving Average."""
        return self.df[column].ewm(span=period, adjust=False).mean()

    def vwap(self) -> pd.Series:
        """Volume Weighted Average Price."""
        typical_price = (self.df["high"] + self.df["low"] + self.df["close"]) / 3
        return (typical_price * self.df["volume"]).cumsum() / self.df["volume"].cumsum()

    def supertrend(self, period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
        """
        Supertrend indicator.

        Returns:
            Tuple of (supertrend_line, direction)
            direction: 1 = bullish, -1 = bearish
        """
        atr = self.atr(period)
        hl2 = (self.df["high"] + self.df["low"]) / 2

        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)

        supertrend = pd.Series(index=self.df.index, dtype=float)
        direction = pd.Series(index=self.df.index, dtype=int)

        supertrend.iloc[0] = upper_band.iloc[0]
        direction.iloc[0] = 1

        for i in range(1, len(self.df)):
            if self.df["close"].iloc[i] > supertrend.iloc[i - 1]:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
            else:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1

        return supertrend, direction

    # ==================== Momentum Indicators ====================

    def rsi(self, period: int = 14) -> pd.Series:
        """Relative Strength Index."""
        delta = self.df["close"].diff()

        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def macd(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD (Moving Average Convergence Divergence).

        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        ema_fast = self.ema(fast)
        ema_slow = self.ema(slow)

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def stochastic(
        self,
        k_period: int = 14,
        d_period: int = 3,
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Stochastic Oscillator.

        Returns:
            Tuple of (%K, %D)
        """
        low_min = self.df["low"].rolling(window=k_period).min()
        high_max = self.df["high"].rolling(window=k_period).max()

        k = 100 * (self.df["close"] - low_min) / (high_max - low_min)
        d = k.rolling(window=d_period).mean()

        return k, d

    def stochastic_rsi(
        self,
        rsi_period: int = 14,
        stoch_period: int = 14,
        k_period: int = 3,
        d_period: int = 3,
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Stochastic RSI.

        Returns:
            Tuple of (StochRSI %K, StochRSI %D)
        """
        rsi = self.rsi(rsi_period)

        rsi_min = rsi.rolling(window=stoch_period).min()
        rsi_max = rsi.rolling(window=stoch_period).max()

        stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min)
        k = stoch_rsi.rolling(window=k_period).mean() * 100
        d = k.rolling(window=d_period).mean()

        return k, d

    def williams_r(self, period: int = 14) -> pd.Series:
        """Williams %R."""
        high_max = self.df["high"].rolling(window=period).max()
        low_min = self.df["low"].rolling(window=period).min()

        return -100 * (high_max - self.df["close"]) / (high_max - low_min)

    def cci(self, period: int = 20) -> pd.Series:
        """Commodity Channel Index."""
        typical_price = (self.df["high"] + self.df["low"] + self.df["close"]) / 3
        sma = typical_price.rolling(window=period).mean()
        mad = typical_price.rolling(window=period).apply(
            lambda x: np.abs(x - x.mean()).mean()
        )

        return (typical_price - sma) / (0.015 * mad)

    # ==================== Volatility Indicators ====================

    def atr(self, period: int = 14) -> pd.Series:
        """Average True Range."""
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def bollinger_bands(
        self,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Bollinger Bands.

        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        middle = self.sma(period)
        std = self.df["close"].rolling(window=period).std()

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        return upper, middle, lower

    def bollinger_bandwidth(self, period: int = 20, std_dev: float = 2.0) -> pd.Series:
        """Bollinger Bandwidth (for squeeze detection)."""
        upper, middle, lower = self.bollinger_bands(period, std_dev)
        return (upper - lower) / middle * 100

    def keltner_channels(
        self,
        ema_period: int = 20,
        atr_period: int = 10,
        multiplier: float = 2.0,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Keltner Channels.

        Returns:
            Tuple of (upper_channel, middle_channel, lower_channel)
        """
        middle = self.ema(ema_period)
        atr = self.atr(atr_period)

        upper = middle + (multiplier * atr)
        lower = middle - (multiplier * atr)

        return upper, middle, lower

    def squeeze_indicator(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        kc_period: int = 20,
        kc_atr_period: int = 10,
        kc_multiplier: float = 1.5,
    ) -> Tuple[pd.Series, pd.Series]:
        """
        TTM Squeeze indicator.

        Returns:
            Tuple of (squeeze_on, momentum)
            squeeze_on: True when BB inside KC (volatility squeeze)
        """
        bb_upper, bb_middle, bb_lower = self.bollinger_bands(bb_period, bb_std)
        kc_upper, kc_middle, kc_lower = self.keltner_channels(
            kc_period, kc_atr_period, kc_multiplier
        )

        # Squeeze is on when BB is inside KC
        squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)

        # Momentum using linear regression
        typical_price = (self.df["high"] + self.df["low"] + self.df["close"]) / 3
        momentum = typical_price - typical_price.rolling(window=bb_period).mean()

        return squeeze_on, momentum

    # ==================== Volume Indicators ====================

    def obv(self) -> pd.Series:
        """On-Balance Volume."""
        obv = pd.Series(index=self.df.index, dtype=float)
        obv.iloc[0] = 0

        for i in range(1, len(self.df)):
            if self.df["close"].iloc[i] > self.df["close"].iloc[i - 1]:
                obv.iloc[i] = obv.iloc[i - 1] + self.df["volume"].iloc[i]
            elif self.df["close"].iloc[i] < self.df["close"].iloc[i - 1]:
                obv.iloc[i] = obv.iloc[i - 1] - self.df["volume"].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i - 1]

        return obv

    def volume_sma(self, period: int = 20) -> pd.Series:
        """Volume Simple Moving Average."""
        return self.df["volume"].rolling(window=period).mean()

    def volume_ratio(self, period: int = 20) -> pd.Series:
        """Current volume vs average volume ratio."""
        avg_volume = self.volume_sma(period)
        return self.df["volume"] / avg_volume

    # ==================== Support/Resistance ====================

    def pivot_points(self) -> Dict[str, float]:
        """
        Calculate pivot points from the last completed period.

        Returns:
            Dictionary with PP, R1, R2, R3, S1, S2, S3
        """
        # Use the previous bar for pivot calculation
        high = float(self.df["high"].iloc[-2])
        low = float(self.df["low"].iloc[-2])
        close = float(self.df["close"].iloc[-2])

        pp = (high + low + close) / 3

        r1 = (2 * pp) - low
        r2 = pp + (high - low)
        r3 = high + 2 * (pp - low)

        s1 = (2 * pp) - high
        s2 = pp - (high - low)
        s3 = low - 2 * (high - pp)

        return {
            "PP": pp,
            "R1": r1,
            "R2": r2,
            "R3": r3,
            "S1": s1,
            "S2": s2,
            "S3": s3,
        }

    def fibonacci_levels(self) -> Dict[str, float]:
        """
        Calculate Fibonacci retracement levels from recent high/low.

        Returns:
            Dictionary with Fibonacci levels
        """
        # Find recent swing high and low (last 50 periods)
        lookback = min(50, len(self.df))
        high = float(self.df["high"].iloc[-lookback:].max())
        low = float(self.df["low"].iloc[-lookback:].min())

        diff = high - low

        return {
            "0.0": high,
            "0.236": high - (diff * 0.236),
            "0.382": high - (diff * 0.382),
            "0.5": high - (diff * 0.5),
            "0.618": high - (diff * 0.618),
            "0.786": high - (diff * 0.786),
            "1.0": low,
        }

    # ==================== Analysis ====================

    def analyze(
        self,
        symbol: str = "UNKNOWN",
        timeframe: str = "M15",
    ) -> AnalysisResult:
        """
        Perform comprehensive technical analysis.

        Returns:
            AnalysisResult with all indicators and recommendations
        """
        indicators = []

        # RSI
        rsi = self.rsi()
        rsi_value = float(rsi.iloc[-1])
        rsi_signal = "neutral"
        if rsi_value < 30:
            rsi_signal = "bullish"  # Oversold
        elif rsi_value > 70:
            rsi_signal = "bearish"  # Overbought

        indicators.append(IndicatorResult(
            name="RSI",
            value=rsi_value,
            signal=rsi_signal,
            strength=abs(50 - rsi_value) * 2,
            details={"period": 14},
        ))

        # MACD
        macd_line, signal_line, histogram = self.macd()
        macd_value = float(histogram.iloc[-1])
        macd_prev = float(histogram.iloc[-2]) if len(histogram) > 1 else 0
        macd_signal = "neutral"
        if macd_value > 0 and macd_value > macd_prev:
            macd_signal = "bullish"
        elif macd_value < 0 and macd_value < macd_prev:
            macd_signal = "bearish"

        indicators.append(IndicatorResult(
            name="MACD",
            value=macd_value,
            signal=macd_signal,
            strength=min(abs(macd_value) * 100, 100),
            details={"macd": float(macd_line.iloc[-1]), "signal": float(signal_line.iloc[-1])},
        ))

        # EMA Trend
        ema_20 = self.ema(20)
        ema_50 = self.ema(50)
        ema_trend = "bullish" if float(ema_20.iloc[-1]) > float(ema_50.iloc[-1]) else "bearish"
        price = float(self.df["close"].iloc[-1])
        ema_strength = abs(price - float(ema_20.iloc[-1])) / price * 100

        indicators.append(IndicatorResult(
            name="EMA_Trend",
            value=float(ema_20.iloc[-1]),
            signal=ema_trend,
            strength=min(ema_strength * 10, 100),
            details={"ema_20": float(ema_20.iloc[-1]), "ema_50": float(ema_50.iloc[-1])},
        ))

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self.bollinger_bands()
        bb_position = (price - float(bb_lower.iloc[-1])) / (float(bb_upper.iloc[-1]) - float(bb_lower.iloc[-1]))
        bb_signal = "neutral"
        if bb_position < 0.2:
            bb_signal = "bullish"  # Near lower band
        elif bb_position > 0.8:
            bb_signal = "bearish"  # Near upper band

        indicators.append(IndicatorResult(
            name="Bollinger_Bands",
            value=bb_position * 100,
            signal=bb_signal,
            strength=abs(50 - bb_position * 100) * 2,
            details={
                "upper": float(bb_upper.iloc[-1]),
                "middle": float(bb_middle.iloc[-1]),
                "lower": float(bb_lower.iloc[-1]),
            },
        ))

        # ATR (for volatility context)
        atr = self.atr()
        atr_value = float(atr.iloc[-1])
        atr_percent = atr_value / price * 100

        indicators.append(IndicatorResult(
            name="ATR",
            value=atr_value,
            signal="neutral",
            strength=min(atr_percent * 20, 100),
            details={"atr_percent": atr_percent},
        ))

        # Stochastic RSI
        stoch_k, stoch_d = self.stochastic_rsi()
        stoch_value = float(stoch_k.iloc[-1])
        stoch_signal = "neutral"
        if stoch_value < 20:
            stoch_signal = "bullish"
        elif stoch_value > 80:
            stoch_signal = "bearish"

        indicators.append(IndicatorResult(
            name="Stochastic_RSI",
            value=stoch_value,
            signal=stoch_signal,
            strength=abs(50 - stoch_value) * 2,
            details={"k": stoch_value, "d": float(stoch_d.iloc[-1])},
        ))

        # Supertrend
        st_line, st_direction = self.supertrend()
        st_signal = "bullish" if st_direction.iloc[-1] == 1 else "bearish"

        indicators.append(IndicatorResult(
            name="Supertrend",
            value=float(st_line.iloc[-1]),
            signal=st_signal,
            strength=75,  # Supertrend is a strong trend indicator
            details={"direction": int(st_direction.iloc[-1])},
        ))

        # Calculate overall trend
        bullish_count = sum(1 for i in indicators if i.signal == "bullish")
        bearish_count = sum(1 for i in indicators if i.signal == "bearish")

        if bullish_count > bearish_count + 1:
            trend = "bullish"
        elif bearish_count > bullish_count + 1:
            trend = "bearish"
        else:
            trend = "neutral"

        trend_strength = (max(bullish_count, bearish_count) / len(indicators)) * 100

        # Get support/resistance levels
        pivots = self.pivot_points()
        support_levels = [pivots["S1"], pivots["S2"], pivots["S3"]]
        resistance_levels = [pivots["R1"], pivots["R2"], pivots["R3"]]

        # Generate recommendation
        if trend == "bullish" and trend_strength > 60:
            recommendation = "BUY"
            confidence = trend_strength
        elif trend == "bearish" and trend_strength > 60:
            recommendation = "SELL"
            confidence = trend_strength
        else:
            recommendation = "HOLD"
            confidence = 50

        return AnalysisResult(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=str(self.df.index[-1]),
            trend=trend,
            trend_strength=trend_strength,
            indicators=indicators,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            recommendation=recommendation,
            confidence=confidence,
        )

    def to_dict(self) -> Dict:
        """Get all indicators as a dictionary."""
        rsi = self.rsi()
        macd_line, signal_line, histogram = self.macd()
        ema_20 = self.ema(20)
        ema_50 = self.ema(50)
        bb_upper, bb_middle, bb_lower = self.bollinger_bands()
        atr = self.atr()
        stoch_k, stoch_d = self.stochastic()

        return {
            "rsi": float(rsi.iloc[-1]),
            "macd": float(macd_line.iloc[-1]),
            "macd_signal": float(signal_line.iloc[-1]),
            "macd_histogram": float(histogram.iloc[-1]),
            "ema_20": float(ema_20.iloc[-1]),
            "ema_50": float(ema_50.iloc[-1]),
            "bb_upper": float(bb_upper.iloc[-1]),
            "bb_middle": float(bb_middle.iloc[-1]),
            "bb_lower": float(bb_lower.iloc[-1]),
            "atr": float(atr.iloc[-1]),
            "stoch_k": float(stoch_k.iloc[-1]),
            "stoch_d": float(stoch_d.iloc[-1]),
            "price": float(self.df["close"].iloc[-1]),
        }
