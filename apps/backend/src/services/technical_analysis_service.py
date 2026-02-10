"""
Technical Analysis Service

Calculates technical indicators and Smart Money Concepts (SMC) for market analysis.
Provides comprehensive technical data for AI trading analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

try:
    import ta
    from ta.momentum import RSIIndicator, StochasticOscillator
    from ta.trend import MACD, ADXIndicator, EMAIndicator, SMAIndicator
    from ta.volatility import AverageTrueRange, BollingerBands
    from ta.volume import VolumeWeightedAveragePrice
    HAS_TA = True
except ImportError:
    HAS_TA = False

from src.services.market_data_service import MarketData


class ZoneType(str, Enum):
    """Types of price zones."""
    SUPPLY = "supply"
    DEMAND = "demand"
    ORDER_BLOCK_BULLISH = "order_block_bullish"
    ORDER_BLOCK_BEARISH = "order_block_bearish"
    FVG_BULLISH = "fvg_bullish"  # Fair Value Gap
    FVG_BEARISH = "fvg_bearish"
    BREAKER_BLOCK = "breaker_block"
    LIQUIDITY_HIGH = "liquidity_high"
    LIQUIDITY_LOW = "liquidity_low"
    SUPPORT = "support"
    RESISTANCE = "resistance"
    PIVOT = "pivot"


class TrendDirection(str, Enum):
    """Market trend direction."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGING = "ranging"


class MarketStructure(str, Enum):
    """Market structure patterns."""
    HH = "higher_high"
    HL = "higher_low"
    LH = "lower_high"
    LL = "lower_low"
    BOS = "break_of_structure"
    CHOCH = "change_of_character"


@dataclass
class PriceZone:
    """A significant price zone."""
    zone_type: ZoneType
    price_high: Decimal
    price_low: Decimal
    strength: float  # 0-100
    timestamp: datetime
    touches: int = 1
    broken: bool = False
    description: str = ""

    @property
    def mid_price(self) -> Decimal:
        return (self.price_high + self.price_low) / 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.zone_type.value,
            "price_high": float(self.price_high),
            "price_low": float(self.price_low),
            "mid_price": float(self.mid_price),
            "strength": self.strength,
            "timestamp": self.timestamp.isoformat(),
            "touches": self.touches,
            "broken": self.broken,
            "description": self.description,
        }


@dataclass
class StructurePoint:
    """A market structure point (swing high/low)."""
    structure_type: MarketStructure
    price: Decimal
    timestamp: datetime
    confirmed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.structure_type.value,
            "price": float(self.price),
            "timestamp": self.timestamp.isoformat(),
            "confirmed": self.confirmed,
        }


@dataclass
class TechnicalIndicators:
    """Collection of technical indicators."""
    # Trend
    ema_9: float | None = None
    ema_21: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None

    # Momentum
    rsi_14: float | None = None
    rsi_7: float | None = None
    stoch_k: float | None = None
    stoch_d: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None

    # Volatility
    atr_14: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    bb_width: float | None = None

    # Trend Strength
    adx: float | None = None
    plus_di: float | None = None
    minus_di: float | None = None

    # Volume
    vwap: float | None = None
    volume_sma: float | None = None
    volume_ratio: float | None = None  # Current vs average

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class FibonacciLevels:
    """Fibonacci retracement and extension levels."""
    # Swing points used
    swing_high: Decimal
    swing_low: Decimal
    direction: str  # "bullish" (low to high) or "bearish" (high to low)

    # Retracement levels (pullback targets)
    retracement_236: Decimal = Decimal("0")
    retracement_382: Decimal = Decimal("0")
    retracement_500: Decimal = Decimal("0")
    retracement_618: Decimal = Decimal("0")
    retracement_786: Decimal = Decimal("0")

    # Extension levels (continuation targets)
    extension_1000: Decimal = Decimal("0")  # 100% = swing size
    extension_1272: Decimal = Decimal("0")
    extension_1618: Decimal = Decimal("0")
    extension_2000: Decimal = Decimal("0")
    extension_2618: Decimal = Decimal("0")

    def to_dict(self) -> dict[str, Any]:
        return {
            "swing_high": float(self.swing_high),
            "swing_low": float(self.swing_low),
            "direction": self.direction,
            "retracement": {
                "23.6%": float(self.retracement_236),
                "38.2%": float(self.retracement_382),
                "50.0%": float(self.retracement_500),
                "61.8%": float(self.retracement_618),
                "78.6%": float(self.retracement_786),
            },
            "extension": {
                "100%": float(self.extension_1000),
                "127.2%": float(self.extension_1272),
                "161.8%": float(self.extension_1618),
                "200%": float(self.extension_2000),
                "261.8%": float(self.extension_2618),
            }
        }


@dataclass
class SmartMoneyTrap:
    """Smart Money Trap (Inducement) detection."""
    trap_type: str  # "bull_trap", "bear_trap", "stop_hunt_high", "stop_hunt_low"
    price_level: Decimal
    description: str
    strength: float  # 0-100 confidence
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.trap_type,
            "price": float(self.price_level),
            "description": self.description,
            "strength": self.strength,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SMCAnalysis:
    """Smart Money Concepts analysis result."""
    # Trend
    trend: TrendDirection = TrendDirection.RANGING
    trend_strength: float = 0.0  # 0-100

    # Structure
    structure_points: list[StructurePoint] = field(default_factory=list)
    last_structure: MarketStructure | None = None

    # Zones
    order_blocks: list[PriceZone] = field(default_factory=list)
    fair_value_gaps: list[PriceZone] = field(default_factory=list)
    supply_zones: list[PriceZone] = field(default_factory=list)
    demand_zones: list[PriceZone] = field(default_factory=list)
    liquidity_pools: list[PriceZone] = field(default_factory=list)

    # Key Levels
    support_levels: list[Decimal] = field(default_factory=list)
    resistance_levels: list[Decimal] = field(default_factory=list)
    pivot_points: dict[str, Decimal] = field(default_factory=dict)

    # Fibonacci levels
    fibonacci: FibonacciLevels | None = None

    # Smart Money Traps (Inducement)
    smart_money_traps: list[SmartMoneyTrap] = field(default_factory=list)

    # Bias
    institutional_bias: str = "neutral"  # bullish, bearish, neutral
    retail_trap_warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trend": self.trend.value,
            "trend_strength": self.trend_strength,
            "structure_points": [sp.to_dict() for sp in self.structure_points[-10:]],  # Last 10
            "last_structure": self.last_structure.value if self.last_structure else None,
            "order_blocks": [ob.to_dict() for ob in self.order_blocks],
            "fair_value_gaps": [fvg.to_dict() for fvg in self.fair_value_gaps],
            "supply_zones": [sz.to_dict() for sz in self.supply_zones],
            "demand_zones": [dz.to_dict() for dz in self.demand_zones],
            "liquidity_pools": [lp.to_dict() for lp in self.liquidity_pools],
            "support_levels": [float(s) for s in self.support_levels],
            "resistance_levels": [float(r) for r in self.resistance_levels],
            "pivot_points": {k: float(v) for k, v in self.pivot_points.items()},
            "fibonacci": self.fibonacci.to_dict() if self.fibonacci else None,
            "smart_money_traps": [smt.to_dict() for smt in self.smart_money_traps],
            "institutional_bias": self.institutional_bias,
            "retail_trap_warning": self.retail_trap_warning,
        }


@dataclass
class FullAnalysis:
    """Complete technical analysis result."""
    symbol: str
    timeframe: str
    current_price: Decimal
    timestamp: datetime

    # Basic
    indicators: TechnicalIndicators
    candle_patterns: list[str] = field(default_factory=list)

    # SMC
    smc: SMCAnalysis = field(default_factory=SMCAnalysis)

    # Multi-timeframe
    mtf_trend: dict[str, TrendDirection] = field(default_factory=dict)
    mtf_bias: str = "neutral"  # Confluence of multiple timeframes

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "current_price": float(self.current_price),
            "timestamp": self.timestamp.isoformat(),
            "indicators": self.indicators.to_dict(),
            "candle_patterns": self.candle_patterns,
            "smc": self.smc.to_dict(),
            "mtf_trend": {k: v.value for k, v in self.mtf_trend.items()},
            "mtf_bias": self.mtf_bias,
        }

    def to_prompt_string(self) -> str:
        """Convert to detailed string for AI prompt."""
        lines = [
            f"=== TECHNICAL ANALYSIS: {self.symbol} ({self.timeframe}) ===",
            f"Current Price: {self.current_price}",
            f"Analysis Time: {self.timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "--- INDICATORS ---",
        ]

        # Indicators
        ind = self.indicators
        if ind.rsi_14:
            rsi_signal = "OVERSOLD" if ind.rsi_14 < 30 else "OVERBOUGHT" if ind.rsi_14 > 70 else "NEUTRAL"
            lines.append(f"RSI(14): {ind.rsi_14:.1f} ({rsi_signal})")

        if ind.macd is not None:
            macd_signal = "BULLISH" if ind.macd > (ind.macd_signal or 0) else "BEARISH"
            lines.append(f"MACD: {ind.macd:.5f} | Signal: {ind.macd_signal:.5f} | Histogram: {ind.macd_histogram:.5f} ({macd_signal})")

        if ind.stoch_k:
            stoch_signal = "OVERSOLD" if ind.stoch_k < 20 else "OVERBOUGHT" if ind.stoch_k > 80 else "NEUTRAL"
            lines.append(f"Stochastic: K={ind.stoch_k:.1f}, D={ind.stoch_d:.1f} ({stoch_signal})")

        if ind.adx:
            trend_str = "STRONG TREND" if ind.adx > 25 else "WEAK/RANGING"
            lines.append(f"ADX: {ind.adx:.1f} ({trend_str}) | +DI: {ind.plus_di:.1f} | -DI: {ind.minus_di:.1f}")

        lines.append("")
        lines.append("--- MOVING AVERAGES ---")
        if ind.ema_9:
            lines.append(f"EMA 9: {ind.ema_9:.5f}")
        if ind.ema_21:
            lines.append(f"EMA 21: {ind.ema_21:.5f}")
        if ind.ema_50:
            lines.append(f"EMA 50: {ind.ema_50:.5f}")
        if ind.ema_200:
            lines.append(f"EMA 200: {ind.ema_200:.5f}")
        if ind.sma_200:
            lines.append(f"SMA 200: {ind.sma_200:.5f}")

        # Price vs MAs
        if ind.ema_200:
            pos = "ABOVE" if float(self.current_price) > ind.ema_200 else "BELOW"
            lines.append(f"Price is {pos} EMA 200 (long-term trend)")

        lines.append("")
        lines.append("--- BOLLINGER BANDS ---")
        if ind.bb_upper:
            bb_pos = "UPPER BAND" if float(self.current_price) > ind.bb_upper else \
                     "LOWER BAND" if float(self.current_price) < ind.bb_lower else "MIDDLE"
            lines.append(f"Upper: {ind.bb_upper:.5f} | Middle: {ind.bb_middle:.5f} | Lower: {ind.bb_lower:.5f}")
            lines.append(f"Price near: {bb_pos}")
            if ind.bb_width:
                volatility = "HIGH" if ind.bb_width > 0.02 else "LOW" if ind.bb_width < 0.01 else "MODERATE"
                lines.append(f"BB Width: {ind.bb_width:.4f} ({volatility} volatility)")

        if ind.atr_14:
            lines.append(f"ATR(14): {ind.atr_14:.5f} (average true range)")

        # SMC Section
        lines.append("")
        lines.append("--- SMART MONEY CONCEPTS ---")
        lines.append(f"Market Trend: {self.smc.trend.value.upper()} (Strength: {self.smc.trend_strength:.0f}%)")
        lines.append(f"Institutional Bias: {self.smc.institutional_bias.upper()}")

        if self.smc.last_structure:
            lines.append(f"Last Structure: {self.smc.last_structure.value.upper()}")

        if self.smc.retail_trap_warning:
            lines.append(f"⚠️ TRAP WARNING: {self.smc.retail_trap_warning}")

        # Structure points
        if self.smc.structure_points:
            lines.append("")
            lines.append("Recent Structure Points:")
            for sp in self.smc.structure_points[-5:]:
                lines.append(f"  • {sp.structure_type.value}: {sp.price} @ {sp.timestamp.strftime('%H:%M')}")

        # Order Blocks
        if self.smc.order_blocks:
            lines.append("")
            lines.append("Order Blocks (Institutional Zones):")
            for ob in self.smc.order_blocks[:5]:
                status = "BROKEN" if ob.broken else "ACTIVE"
                lines.append(f"  • {ob.zone_type.value}: {ob.price_low:.5f} - {ob.price_high:.5f} (Strength: {ob.strength:.0f}%, {status})")

        # FVGs
        if self.smc.fair_value_gaps:
            lines.append("")
            lines.append("Fair Value Gaps (Imbalances):")
            for fvg in self.smc.fair_value_gaps[:5]:
                lines.append(f"  • {fvg.zone_type.value}: {fvg.price_low:.5f} - {fvg.price_high:.5f}")

        # Supply/Demand
        if self.smc.supply_zones:
            lines.append("")
            lines.append("Supply Zones:")
            for sz in self.smc.supply_zones[:3]:
                lines.append(f"  • {sz.price_low:.5f} - {sz.price_high:.5f} (Strength: {sz.strength:.0f}%, Touches: {sz.touches})")

        if self.smc.demand_zones:
            lines.append("")
            lines.append("Demand Zones:")
            for dz in self.smc.demand_zones[:3]:
                lines.append(f"  • {dz.price_low:.5f} - {dz.price_high:.5f} (Strength: {dz.strength:.0f}%, Touches: {dz.touches})")

        # Liquidity
        if self.smc.liquidity_pools:
            lines.append("")
            lines.append("Liquidity Pools (Potential Targets):")
            for lp in self.smc.liquidity_pools[:4]:
                lines.append(f"  • {lp.zone_type.value}: {lp.mid_price:.5f}")

        # Support/Resistance
        if self.smc.support_levels or self.smc.resistance_levels:
            lines.append("")
            lines.append("Key Levels:")
            if self.smc.resistance_levels:
                lines.append(f"  Resistance: {', '.join(f'{r:.5f}' for r in self.smc.resistance_levels[:3])}")
            if self.smc.support_levels:
                lines.append(f"  Support: {', '.join(f'{s:.5f}' for s in self.smc.support_levels[:3])}")

        # Pivots
        if self.smc.pivot_points:
            lines.append("")
            lines.append("Pivot Points:")
            # Group pivots by type
            standard = {k: v for k, v in self.smc.pivot_points.items() if not k.startswith(('Fib_', 'Cam_', 'Wood_'))}
            fib = {k: v for k, v in self.smc.pivot_points.items() if k.startswith('Fib_')}
            cam = {k: v for k, v in self.smc.pivot_points.items() if k.startswith('Cam_')}
            wood = {k: v for k, v in self.smc.pivot_points.items() if k.startswith('Wood_')}

            if standard:
                lines.append("  Standard:")
                for name, price in standard.items():
                    lines.append(f"    {name}: {price:.5f}")
            if fib:
                lines.append("  Fibonacci:")
                for name, price in fib.items():
                    lines.append(f"    {name.replace('Fib_', '')}: {price:.5f}")
            if cam:
                lines.append("  Camarilla:")
                for name, price in cam.items():
                    lines.append(f"    {name.replace('Cam_', '')}: {price:.5f}")
            if wood:
                lines.append("  Woodie:")
                for name, price in wood.items():
                    lines.append(f"    {name.replace('Wood_', '')}: {price:.5f}")

        # Fibonacci Retracement/Extension
        if self.smc.fibonacci:
            lines.append("")
            lines.append("--- FIBONACCI LEVELS ---")
            fib = self.smc.fibonacci
            lines.append(f"Swing: {fib.swing_low:.5f} → {fib.swing_high:.5f} ({fib.direction.upper()})")
            lines.append("Retracements:")
            lines.append(f"  23.6%: {fib.retracement_236:.5f}")
            lines.append(f"  38.2%: {fib.retracement_382:.5f}")
            lines.append(f"  50.0%: {fib.retracement_500:.5f}")
            lines.append(f"  61.8%: {fib.retracement_618:.5f} (Golden Ratio)")
            lines.append(f"  78.6%: {fib.retracement_786:.5f}")
            lines.append("Extensions:")
            lines.append(f"  127.2%: {fib.extension_1272:.5f}")
            lines.append(f"  161.8%: {fib.extension_1618:.5f} (Golden Extension)")
            lines.append(f"  200%: {fib.extension_2000:.5f}")
            lines.append(f"  261.8%: {fib.extension_2618:.5f}")

        # Smart Money Traps (Inducement)
        if self.smc.smart_money_traps:
            lines.append("")
            lines.append("--- SMART MONEY TRAPS (INDUCEMENT) ---")
            for trap in self.smc.smart_money_traps:
                emoji = "🐂" if "bull" in trap.trap_type else "🐻" if "bear" in trap.trap_type else "🎯"
                lines.append(f"  {emoji} {trap.trap_type.upper()}: {trap.price_level:.5f}")
                lines.append(f"      {trap.description}")
                lines.append(f"      Forza: {trap.strength:.0f}%")

        # MTF
        if self.mtf_trend:
            lines.append("")
            lines.append("--- MULTI-TIMEFRAME ANALYSIS ---")
            for tf, trend in self.mtf_trend.items():
                lines.append(f"  {tf}: {trend.value.upper()}")
            lines.append(f"  Overall MTF Bias: {self.mtf_bias.upper()}")

        # Candle patterns
        if self.candle_patterns:
            lines.append("")
            lines.append("--- CANDLE PATTERNS ---")
            for pattern in self.candle_patterns:
                lines.append(f"  • {pattern}")

        return "\n".join(lines)


class TechnicalAnalysisService:
    """
    Service for calculating technical indicators and SMC analysis.
    """

    def calculate_indicators(self, df: pd.DataFrame) -> TechnicalIndicators:
        """Calculate all technical indicators from OHLCV DataFrame."""
        if df.empty or len(df) < 20:
            return TechnicalIndicators()

        indicators = TechnicalIndicators()

        try:
            close = df['close']
            high = df['high']
            low = df['low']
            volume = df['volume'] if 'volume' in df else pd.Series([0] * len(df))

            # EMAs
            if len(df) >= 9:
                indicators.ema_9 = float(close.ewm(span=9, adjust=False).mean().iloc[-1])
            if len(df) >= 21:
                indicators.ema_21 = float(close.ewm(span=21, adjust=False).mean().iloc[-1])
            if len(df) >= 50:
                indicators.ema_50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
            if len(df) >= 200:
                indicators.ema_200 = float(close.ewm(span=200, adjust=False).mean().iloc[-1])

            # SMAs
            if len(df) >= 20:
                indicators.sma_20 = float(close.rolling(window=20).mean().iloc[-1])
            if len(df) >= 50:
                indicators.sma_50 = float(close.rolling(window=50).mean().iloc[-1])
            if len(df) >= 200:
                indicators.sma_200 = float(close.rolling(window=200).mean().iloc[-1])

            # RSI
            if len(df) >= 14:
                delta = close.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                indicators.rsi_14 = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None

            if len(df) >= 7:
                delta = close.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                indicators.rsi_7 = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None

            # MACD
            if len(df) >= 26:
                ema12 = close.ewm(span=12, adjust=False).mean()
                ema26 = close.ewm(span=26, adjust=False).mean()
                macd_line = ema12 - ema26
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                histogram = macd_line - signal_line

                indicators.macd = float(macd_line.iloc[-1])
                indicators.macd_signal = float(signal_line.iloc[-1])
                indicators.macd_histogram = float(histogram.iloc[-1])

            # Stochastic
            if len(df) >= 14:
                low_14 = low.rolling(window=14).min()
                high_14 = high.rolling(window=14).max()
                stoch_k = 100 * (close - low_14) / (high_14 - low_14)
                stoch_d = stoch_k.rolling(window=3).mean()

                indicators.stoch_k = float(stoch_k.iloc[-1]) if not pd.isna(stoch_k.iloc[-1]) else None
                indicators.stoch_d = float(stoch_d.iloc[-1]) if not pd.isna(stoch_d.iloc[-1]) else None

            # Bollinger Bands
            if len(df) >= 20:
                sma20 = close.rolling(window=20).mean()
                std20 = close.rolling(window=20).std()
                indicators.bb_upper = float(sma20.iloc[-1] + 2 * std20.iloc[-1])
                indicators.bb_middle = float(sma20.iloc[-1])
                indicators.bb_lower = float(sma20.iloc[-1] - 2 * std20.iloc[-1])
                indicators.bb_width = (indicators.bb_upper - indicators.bb_lower) / indicators.bb_middle

            # ATR
            if len(df) >= 14:
                tr1 = high - low
                tr2 = abs(high - close.shift())
                tr3 = abs(low - close.shift())
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr = tr.rolling(window=14).mean()
                indicators.atr_14 = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else None

            # ADX
            if len(df) >= 14:
                plus_dm = high.diff()
                minus_dm = -low.diff()
                plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
                minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

                tr1 = high - low
                tr2 = abs(high - close.shift())
                tr3 = abs(low - close.shift())
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr14 = tr.rolling(window=14).mean()

                plus_di = 100 * (plus_dm.rolling(window=14).mean() / atr14)
                minus_di = 100 * (minus_dm.rolling(window=14).mean() / atr14)

                dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
                adx = dx.rolling(window=14).mean()

                indicators.adx = float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else None
                indicators.plus_di = float(plus_di.iloc[-1]) if not pd.isna(plus_di.iloc[-1]) else None
                indicators.minus_di = float(minus_di.iloc[-1]) if not pd.isna(minus_di.iloc[-1]) else None

            # Volume analysis
            if volume.sum() > 0:
                vol_sma = volume.rolling(window=20).mean()
                indicators.volume_sma = float(vol_sma.iloc[-1]) if not pd.isna(vol_sma.iloc[-1]) else None
                if indicators.volume_sma and indicators.volume_sma > 0:
                    indicators.volume_ratio = float(volume.iloc[-1] / indicators.volume_sma)

                # VWAP calculation
                if len(df) >= 1:
                    typical_price = (high + low + close) / 3
                    vwap = (typical_price * volume).cumsum() / volume.cumsum()
                    indicators.vwap = float(vwap.iloc[-1]) if not pd.isna(vwap.iloc[-1]) else None

        except Exception as e:
            print(f"Error calculating indicators: {e}")

        return indicators

    def analyze_smc(self, df: pd.DataFrame, current_price: Decimal) -> SMCAnalysis:
        """Analyze Smart Money Concepts from price data."""
        smc = SMCAnalysis()

        if df.empty or len(df) < 20:
            return smc

        try:
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            timestamps = df.index.tolist()

            # Detect trend
            smc.trend, smc.trend_strength = self._detect_trend(df)

            # Find swing points (structure)
            smc.structure_points = self._find_structure_points(df)
            if smc.structure_points:
                smc.last_structure = smc.structure_points[-1].structure_type

            # Find Order Blocks
            smc.order_blocks = self._find_order_blocks(df, current_price)

            # Find Fair Value Gaps
            smc.fair_value_gaps = self._find_fvg(df, current_price)

            # Find Supply/Demand zones
            smc.supply_zones, smc.demand_zones = self._find_supply_demand(df, current_price)

            # Find Liquidity pools
            smc.liquidity_pools = self._find_liquidity_pools(df, current_price)

            # Calculate support/resistance
            smc.support_levels, smc.resistance_levels = self._find_sr_levels(df, current_price)

            # Calculate pivot points (all types: standard, fibonacci, camarilla, woodie)
            smc.pivot_points = self._calculate_pivots(df, "all")

            # Calculate Fibonacci levels
            smc.fibonacci = self._calculate_fibonacci(df)

            # Detect Smart Money Traps (Inducement)
            smc.smart_money_traps = self._detect_smart_money_traps(df, current_price)

            # Determine institutional bias
            smc.institutional_bias = self._determine_bias(smc, current_price)

            # Check for retail traps
            smc.retail_trap_warning = self._check_retail_trap(smc, df, current_price)

        except Exception as e:
            print(f"Error in SMC analysis: {e}")

        return smc

    def _detect_trend(self, df: pd.DataFrame) -> tuple[TrendDirection, float]:
        """Detect market trend and strength."""
        if len(df) < 20:
            return TrendDirection.RANGING, 0.0

        close = df['close']
        ema20 = close.ewm(span=20, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean() if len(df) >= 50 else ema20

        current = close.iloc[-1]
        prev_10 = close.iloc[-10] if len(close) >= 10 else close.iloc[0]

        # Price above/below EMAs
        above_ema20 = current > ema20.iloc[-1]
        above_ema50 = current > ema50.iloc[-1]

        # Higher highs/lows check
        recent_highs = df['high'].iloc[-10:].values
        recent_lows = df['low'].iloc[-10:].values

        hh = recent_highs[-1] > np.max(recent_highs[:-1]) if len(recent_highs) > 1 else False
        hl = recent_lows[-1] > np.min(recent_lows[:-1]) if len(recent_lows) > 1 else False
        lh = recent_highs[-1] < np.max(recent_highs[:-1]) if len(recent_highs) > 1 else False
        ll = recent_lows[-1] < np.min(recent_lows[:-1]) if len(recent_lows) > 1 else False

        # Calculate strength
        strength = 0
        if above_ema20:
            strength += 20
        if above_ema50:
            strength += 20
        if hh:
            strength += 15
        if hl:
            strength += 15

        # Determine trend
        if above_ema20 and above_ema50 and (hh or hl):
            return TrendDirection.BULLISH, min(strength + 30, 100)
        elif not above_ema20 and not above_ema50 and (lh or ll):
            return TrendDirection.BEARISH, min(strength + 30, 100)
        else:
            return TrendDirection.RANGING, max(0, 50 - strength)

    def _find_structure_points(self, df: pd.DataFrame, lookback: int = 5) -> list[StructurePoint]:
        """Find swing highs and lows (market structure)."""
        points = []
        high = df['high'].values
        low = df['low'].values
        timestamps = df.index.tolist()

        for i in range(lookback, len(df) - lookback):
            # Swing High
            if high[i] == max(high[i-lookback:i+lookback+1]):
                # Check if higher or lower than previous swing high
                prev_highs = [p for p in points if p.structure_type in [MarketStructure.HH, MarketStructure.LH]]
                if prev_highs:
                    if high[i] > float(prev_highs[-1].price):
                        struct_type = MarketStructure.HH
                    else:
                        struct_type = MarketStructure.LH
                else:
                    struct_type = MarketStructure.HH

                points.append(StructurePoint(
                    structure_type=struct_type,
                    price=Decimal(str(high[i])),
                    timestamp=timestamps[i] if isinstance(timestamps[i], datetime) else datetime.now(),
                ))

            # Swing Low
            if low[i] == min(low[i-lookback:i+lookback+1]):
                prev_lows = [p for p in points if p.structure_type in [MarketStructure.HL, MarketStructure.LL]]
                if prev_lows:
                    if low[i] > float(prev_lows[-1].price):
                        struct_type = MarketStructure.HL
                    else:
                        struct_type = MarketStructure.LL
                else:
                    struct_type = MarketStructure.HL

                points.append(StructurePoint(
                    structure_type=struct_type,
                    price=Decimal(str(low[i])),
                    timestamp=timestamps[i] if isinstance(timestamps[i], datetime) else datetime.now(),
                ))

        return points

    def _find_order_blocks(self, df: pd.DataFrame, current_price: Decimal) -> list[PriceZone]:
        """Find Order Blocks - last candle before a strong move."""
        blocks = []
        open_prices = df['open'].values
        close_prices = df['close'].values
        high_prices = df['high'].values
        low_prices = df['low'].values
        timestamps = df.index.tolist()

        atr = (df['high'] - df['low']).rolling(14).mean().values

        for i in range(len(df) - 3):
            # Check for strong bullish move (potential demand OB)
            if i + 2 < len(df):
                move = close_prices[i+2] - close_prices[i]
                if atr[i] and move > 2 * atr[i]:  # Strong bullish move
                    # The OB is the last bearish candle before the move
                    if close_prices[i] < open_prices[i]:  # Bearish candle
                        blocks.append(PriceZone(
                            zone_type=ZoneType.ORDER_BLOCK_BULLISH,
                            price_high=Decimal(str(high_prices[i])),
                            price_low=Decimal(str(low_prices[i])),
                            strength=min(100, 50 + (move / atr[i]) * 10) if atr[i] else 60,
                            timestamp=timestamps[i] if isinstance(timestamps[i], datetime) else datetime.now(),
                            broken=float(current_price) < low_prices[i],
                            description="Bullish Order Block - potential demand zone",
                        ))

                # Check for strong bearish move (potential supply OB)
                move = close_prices[i] - close_prices[i+2]
                if atr[i] and move > 2 * atr[i]:  # Strong bearish move
                    if close_prices[i] > open_prices[i]:  # Bullish candle
                        blocks.append(PriceZone(
                            zone_type=ZoneType.ORDER_BLOCK_BEARISH,
                            price_high=Decimal(str(high_prices[i])),
                            price_low=Decimal(str(low_prices[i])),
                            strength=min(100, 50 + (move / atr[i]) * 10) if atr[i] else 60,
                            timestamp=timestamps[i] if isinstance(timestamps[i], datetime) else datetime.now(),
                            broken=float(current_price) > high_prices[i],
                            description="Bearish Order Block - potential supply zone",
                        ))

        # Keep only recent, unbroken blocks
        return [b for b in blocks if not b.broken][-5:]

    def _find_fvg(self, df: pd.DataFrame, current_price: Decimal) -> list[PriceZone]:
        """Find Fair Value Gaps (Imbalances)."""
        gaps = []
        high_prices = df['high'].values
        low_prices = df['low'].values
        timestamps = df.index.tolist()

        for i in range(1, len(df) - 1):
            # Bullish FVG: gap between candle 1 high and candle 3 low
            if low_prices[i+1] > high_prices[i-1]:
                gap_size = low_prices[i+1] - high_prices[i-1]
                if gap_size > 0:
                    gaps.append(PriceZone(
                        zone_type=ZoneType.FVG_BULLISH,
                        price_high=Decimal(str(low_prices[i+1])),
                        price_low=Decimal(str(high_prices[i-1])),
                        strength=70,
                        timestamp=timestamps[i] if isinstance(timestamps[i], datetime) else datetime.now(),
                        broken=float(current_price) < high_prices[i-1],
                        description="Bullish FVG - unfilled gap, expect price to return",
                    ))

            # Bearish FVG
            if high_prices[i+1] < low_prices[i-1]:
                gap_size = low_prices[i-1] - high_prices[i+1]
                if gap_size > 0:
                    gaps.append(PriceZone(
                        zone_type=ZoneType.FVG_BEARISH,
                        price_high=Decimal(str(low_prices[i-1])),
                        price_low=Decimal(str(high_prices[i+1])),
                        strength=70,
                        timestamp=timestamps[i] if isinstance(timestamps[i], datetime) else datetime.now(),
                        broken=float(current_price) > low_prices[i-1],
                        description="Bearish FVG - unfilled gap, expect price to return",
                    ))

        return [g for g in gaps if not g.broken][-5:]

    def _find_supply_demand(self, df: pd.DataFrame, current_price: Decimal) -> tuple[list[PriceZone], list[PriceZone]]:
        """Find Supply and Demand zones."""
        supply = []
        demand = []

        high_prices = df['high'].values
        low_prices = df['low'].values
        close_prices = df['close'].values
        open_prices = df['open'].values
        timestamps = df.index.tolist()
        volumes = df['volume'].values if 'volume' in df else [0] * len(df)

        avg_volume = np.mean(volumes) if np.sum(volumes) > 0 else 1

        for i in range(2, len(df) - 2):
            # Strong bullish candle from consolidation = Demand zone
            body = abs(close_prices[i] - open_prices[i])
            prev_range = high_prices[i-1] - low_prices[i-1]

            if close_prices[i] > open_prices[i] and body > 1.5 * prev_range:
                strength = 60
                if volumes[i] > avg_volume * 1.5:
                    strength += 20
                demand.append(PriceZone(
                    zone_type=ZoneType.DEMAND,
                    price_high=Decimal(str(max(open_prices[i], close_prices[i-1]))),
                    price_low=Decimal(str(low_prices[i])),
                    strength=strength,
                    timestamp=timestamps[i] if isinstance(timestamps[i], datetime) else datetime.now(),
                    description="Demand zone - strong buying interest",
                ))

            # Strong bearish candle from consolidation = Supply zone
            if close_prices[i] < open_prices[i] and body > 1.5 * prev_range:
                strength = 60
                if volumes[i] > avg_volume * 1.5:
                    strength += 20
                supply.append(PriceZone(
                    zone_type=ZoneType.SUPPLY,
                    price_high=Decimal(str(high_prices[i])),
                    price_low=Decimal(str(min(open_prices[i], close_prices[i-1]))),
                    strength=strength,
                    timestamp=timestamps[i] if isinstance(timestamps[i], datetime) else datetime.now(),
                    description="Supply zone - strong selling interest",
                ))

        return supply[-3:], demand[-3:]

    def _find_liquidity_pools(self, df: pd.DataFrame, current_price: Decimal) -> list[PriceZone]:
        """Find liquidity pools (equal highs/lows, stop hunt levels)."""
        pools = []
        high_prices = df['high'].values
        low_prices = df['low'].values
        timestamps = df.index.tolist()

        # Find equal highs (buy-side liquidity)
        for i in range(len(df) - 5):
            highs_in_range = high_prices[i:i+5]
            if np.std(highs_in_range) < np.mean(highs_in_range) * 0.001:  # Very close highs
                pools.append(PriceZone(
                    zone_type=ZoneType.LIQUIDITY_HIGH,
                    price_high=Decimal(str(np.max(highs_in_range) * 1.001)),
                    price_low=Decimal(str(np.max(highs_in_range))),
                    strength=75,
                    timestamp=timestamps[i] if isinstance(timestamps[i], datetime) else datetime.now(),
                    description="Buy-side liquidity - stop losses above equal highs",
                ))

        # Find equal lows (sell-side liquidity)
        for i in range(len(df) - 5):
            lows_in_range = low_prices[i:i+5]
            if np.std(lows_in_range) < np.mean(lows_in_range) * 0.001:
                pools.append(PriceZone(
                    zone_type=ZoneType.LIQUIDITY_LOW,
                    price_high=Decimal(str(np.min(lows_in_range))),
                    price_low=Decimal(str(np.min(lows_in_range) * 0.999)),
                    strength=75,
                    timestamp=timestamps[i] if isinstance(timestamps[i], datetime) else datetime.now(),
                    description="Sell-side liquidity - stop losses below equal lows",
                ))

        return pools[-4:]

    def _find_sr_levels(self, df: pd.DataFrame, current_price: Decimal) -> tuple[list[Decimal], list[Decimal]]:
        """Find support and resistance levels."""
        high_prices = df['high'].values
        low_prices = df['low'].values
        close_prices = df['close'].values
        current = float(current_price)

        # Find swing highs for resistance
        resistance = []
        support = []

        for i in range(5, len(df) - 5):
            # Swing high
            if high_prices[i] == max(high_prices[i-5:i+6]):
                if high_prices[i] > current:
                    resistance.append(Decimal(str(high_prices[i])))

            # Swing low
            if low_prices[i] == min(low_prices[i-5:i+6]):
                if low_prices[i] < current:
                    support.append(Decimal(str(low_prices[i])))

        # Sort and deduplicate
        resistance = sorted(set(resistance))[:3]
        support = sorted(set(support), reverse=True)[:3]

        return support, resistance

    def _calculate_pivots(self, df: pd.DataFrame, pivot_type: str = "all") -> dict[str, Decimal]:
        """
        Calculate pivot points with multiple methods.

        Args:
            df: OHLCV DataFrame
            pivot_type: "standard", "fibonacci", "camarilla", "woodie", or "all"
        """
        if len(df) < 2:
            return {}

        # Use previous day/period for pivot calculation
        high = df['high'].iloc[-2] if len(df) > 1 else df['high'].iloc[-1]
        low = df['low'].iloc[-2] if len(df) > 1 else df['low'].iloc[-1]
        close = df['close'].iloc[-2] if len(df) > 1 else df['close'].iloc[-1]
        open_price = df['open'].iloc[-1]  # Current open for Woodie

        pivots = {}

        # Standard Pivot Points
        if pivot_type in ["standard", "all"]:
            pivot = (high + low + close) / 3
            pivots["PP"] = Decimal(str(round(pivot, 5)))
            pivots["R1"] = Decimal(str(round(2 * pivot - low, 5)))
            pivots["R2"] = Decimal(str(round(pivot + (high - low), 5)))
            pivots["R3"] = Decimal(str(round(high + 2 * (pivot - low), 5)))
            pivots["S1"] = Decimal(str(round(2 * pivot - high, 5)))
            pivots["S2"] = Decimal(str(round(pivot - (high - low), 5)))
            pivots["S3"] = Decimal(str(round(low - 2 * (high - pivot), 5)))

        # Fibonacci Pivot Points
        if pivot_type in ["fibonacci", "all"]:
            pivot = (high + low + close) / 3
            range_hl = high - low
            pivots["Fib_PP"] = Decimal(str(round(pivot, 5)))
            pivots["Fib_R1"] = Decimal(str(round(pivot + 0.382 * range_hl, 5)))
            pivots["Fib_R2"] = Decimal(str(round(pivot + 0.618 * range_hl, 5)))
            pivots["Fib_R3"] = Decimal(str(round(pivot + 1.000 * range_hl, 5)))
            pivots["Fib_S1"] = Decimal(str(round(pivot - 0.382 * range_hl, 5)))
            pivots["Fib_S2"] = Decimal(str(round(pivot - 0.618 * range_hl, 5)))
            pivots["Fib_S3"] = Decimal(str(round(pivot - 1.000 * range_hl, 5)))

        # Camarilla Pivot Points
        if pivot_type in ["camarilla", "all"]:
            range_hl = high - low
            pivots["Cam_R1"] = Decimal(str(round(close + range_hl * 1.1 / 12, 5)))
            pivots["Cam_R2"] = Decimal(str(round(close + range_hl * 1.1 / 6, 5)))
            pivots["Cam_R3"] = Decimal(str(round(close + range_hl * 1.1 / 4, 5)))
            pivots["Cam_R4"] = Decimal(str(round(close + range_hl * 1.1 / 2, 5)))
            pivots["Cam_S1"] = Decimal(str(round(close - range_hl * 1.1 / 12, 5)))
            pivots["Cam_S2"] = Decimal(str(round(close - range_hl * 1.1 / 6, 5)))
            pivots["Cam_S3"] = Decimal(str(round(close - range_hl * 1.1 / 4, 5)))
            pivots["Cam_S4"] = Decimal(str(round(close - range_hl * 1.1 / 2, 5)))

        # Woodie Pivot Points
        if pivot_type in ["woodie", "all"]:
            pivot = (high + low + 2 * open_price) / 4
            pivots["Wood_PP"] = Decimal(str(round(pivot, 5)))
            pivots["Wood_R1"] = Decimal(str(round(2 * pivot - low, 5)))
            pivots["Wood_R2"] = Decimal(str(round(pivot + high - low, 5)))
            pivots["Wood_S1"] = Decimal(str(round(2 * pivot - high, 5)))
            pivots["Wood_S2"] = Decimal(str(round(pivot - high + low, 5)))

        return pivots

    def _calculate_fibonacci(self, df: pd.DataFrame, lookback: int = 50) -> FibonacciLevels | None:
        """
        Calculate Fibonacci retracement and extension levels.

        Finds the most significant swing high and swing low in the lookback period
        and calculates Fibonacci levels based on them.
        """
        if len(df) < lookback:
            lookback = len(df)
        if lookback < 10:
            return None

        recent_df = df.iloc[-lookback:]
        high_prices = recent_df['high'].values
        low_prices = recent_df['low'].values
        close_prices = recent_df['close'].values

        # Find swing high and swing low
        swing_high_idx = np.argmax(high_prices)
        swing_low_idx = np.argmin(low_prices)

        swing_high = Decimal(str(high_prices[swing_high_idx]))
        swing_low = Decimal(str(low_prices[swing_low_idx]))

        # Determine direction (which came first)
        if swing_low_idx < swing_high_idx:
            # Low came first = bullish move (retracing down)
            direction = "bullish"
        else:
            # High came first = bearish move (retracing up)
            direction = "bearish"

        # Calculate range
        range_size = swing_high - swing_low

        if range_size == 0:
            return None

        # Calculate Fibonacci levels
        fib = FibonacciLevels(
            swing_high=swing_high,
            swing_low=swing_low,
            direction=direction,
        )

        if direction == "bullish":
            # Retracements from high going down
            fib.retracement_236 = swing_high - range_size * Decimal("0.236")
            fib.retracement_382 = swing_high - range_size * Decimal("0.382")
            fib.retracement_500 = swing_high - range_size * Decimal("0.500")
            fib.retracement_618 = swing_high - range_size * Decimal("0.618")
            fib.retracement_786 = swing_high - range_size * Decimal("0.786")

            # Extensions above swing high
            fib.extension_1000 = swing_high
            fib.extension_1272 = swing_high + range_size * Decimal("0.272")
            fib.extension_1618 = swing_high + range_size * Decimal("0.618")
            fib.extension_2000 = swing_high + range_size
            fib.extension_2618 = swing_high + range_size * Decimal("1.618")
        else:
            # Retracements from low going up
            fib.retracement_236 = swing_low + range_size * Decimal("0.236")
            fib.retracement_382 = swing_low + range_size * Decimal("0.382")
            fib.retracement_500 = swing_low + range_size * Decimal("0.500")
            fib.retracement_618 = swing_low + range_size * Decimal("0.618")
            fib.retracement_786 = swing_low + range_size * Decimal("0.786")

            # Extensions below swing low
            fib.extension_1000 = swing_low
            fib.extension_1272 = swing_low - range_size * Decimal("0.272")
            fib.extension_1618 = swing_low - range_size * Decimal("0.618")
            fib.extension_2000 = swing_low - range_size
            fib.extension_2618 = swing_low - range_size * Decimal("1.618")

        return fib

    def _detect_smart_money_traps(self, df: pd.DataFrame, current_price: Decimal) -> list[SmartMoneyTrap]:
        """
        Detect Smart Money Traps (Inducement/Stop Hunts).

        These are price movements designed to trigger retail stop losses
        before reversing in the intended direction.

        Types:
        - Bull Trap: False breakout above resistance
        - Bear Trap: False breakdown below support
        - Stop Hunt High: Quick spike to take out buy stops
        - Stop Hunt Low: Quick spike to take out sell stops
        """
        traps = []

        if len(df) < 20:
            return traps

        high_prices = df['high'].values
        low_prices = df['low'].values
        close_prices = df['close'].values
        open_prices = df['open'].values
        timestamps = df.index.tolist()

        # Calculate ATR for significance threshold
        atr = (df['high'] - df['low']).rolling(14).mean().values

        # Look for traps in recent candles
        for i in range(-10, -1):
            try:
                if pd.isna(atr[i]) or atr[i] == 0:
                    continue

                # Bull Trap: Spike above recent highs then closes back below
                recent_high = np.max(high_prices[i-10:i])
                if high_prices[i] > recent_high and close_prices[i] < recent_high:
                    # Check if next candle confirms (closes even lower)
                    if i + 1 < len(close_prices) and close_prices[i+1] < close_prices[i]:
                        trap_strength = min(100, 50 + (high_prices[i] - recent_high) / atr[i] * 20)
                        traps.append(SmartMoneyTrap(
                            trap_type="bull_trap",
                            price_level=Decimal(str(high_prices[i])),
                            description=f"Falsa rottura sopra {recent_high:.5f}, prezzo rientrato. Possibile trappola per i compratori.",
                            strength=float(trap_strength),
                            timestamp=timestamps[i] if isinstance(timestamps[i], datetime) else datetime.now(),
                        ))

                # Bear Trap: Spike below recent lows then closes back above
                recent_low = np.min(low_prices[i-10:i])
                if low_prices[i] < recent_low and close_prices[i] > recent_low:
                    # Check if next candle confirms (closes even higher)
                    if i + 1 < len(close_prices) and close_prices[i+1] > close_prices[i]:
                        trap_strength = min(100, 50 + (recent_low - low_prices[i]) / atr[i] * 20)
                        traps.append(SmartMoneyTrap(
                            trap_type="bear_trap",
                            price_level=Decimal(str(low_prices[i])),
                            description=f"Falsa rottura sotto {recent_low:.5f}, prezzo rientrato. Possibile trappola per i venditori.",
                            strength=float(trap_strength),
                            timestamp=timestamps[i] if isinstance(timestamps[i], datetime) else datetime.now(),
                        ))

                # Stop Hunt High: Long upper wick (>60% of candle) after ranging
                candle_range = high_prices[i] - low_prices[i]
                if candle_range > 0:
                    upper_wick = high_prices[i] - max(open_prices[i], close_prices[i])
                    lower_wick = min(open_prices[i], close_prices[i]) - low_prices[i]

                    if upper_wick > 0.6 * candle_range and upper_wick > atr[i] * 0.5:
                        traps.append(SmartMoneyTrap(
                            trap_type="stop_hunt_high",
                            price_level=Decimal(str(high_prices[i])),
                            description=f"Caccia agli stop sopra {high_prices[i]:.5f}. Lunga ombra superiore indica rigetto.",
                            strength=float(min(100, 40 + upper_wick / candle_range * 60)),
                            timestamp=timestamps[i] if isinstance(timestamps[i], datetime) else datetime.now(),
                        ))

                    # Stop Hunt Low: Long lower wick (>60% of candle)
                    if lower_wick > 0.6 * candle_range and lower_wick > atr[i] * 0.5:
                        traps.append(SmartMoneyTrap(
                            trap_type="stop_hunt_low",
                            price_level=Decimal(str(low_prices[i])),
                            description=f"Caccia agli stop sotto {low_prices[i]:.5f}. Lunga ombra inferiore indica rigetto.",
                            strength=float(min(100, 40 + lower_wick / candle_range * 60)),
                            timestamp=timestamps[i] if isinstance(timestamps[i], datetime) else datetime.now(),
                        ))

            except (IndexError, ValueError):
                continue

        # Keep only the most significant traps (top 5 by strength)
        traps.sort(key=lambda x: x.strength, reverse=True)
        return traps[:5]

    def _determine_bias(self, smc: SMCAnalysis, current_price: Decimal) -> str:
        """Determine institutional bias based on SMC."""
        bullish_signals = 0
        bearish_signals = 0

        # Trend
        if smc.trend == TrendDirection.BULLISH:
            bullish_signals += 2
        elif smc.trend == TrendDirection.BEARISH:
            bearish_signals += 2

        # Structure
        if smc.last_structure in [MarketStructure.HH, MarketStructure.HL]:
            bullish_signals += 1
        elif smc.last_structure in [MarketStructure.LH, MarketStructure.LL]:
            bearish_signals += 1

        # Order blocks proximity
        for ob in smc.order_blocks:
            if ob.zone_type == ZoneType.ORDER_BLOCK_BULLISH and float(current_price) <= float(ob.price_high):
                bullish_signals += 1
            elif ob.zone_type == ZoneType.ORDER_BLOCK_BEARISH and float(current_price) >= float(ob.price_low):
                bearish_signals += 1

        if bullish_signals > bearish_signals + 1:
            return "bullish"
        elif bearish_signals > bullish_signals + 1:
            return "bearish"
        return "neutral"

    def _check_retail_trap(self, smc: SMCAnalysis, df: pd.DataFrame, current_price: Decimal) -> str | None:
        """Check for potential retail traps."""
        # Check if price is near liquidity that could be swept
        for lp in smc.liquidity_pools:
            diff = abs(float(current_price) - float(lp.mid_price))
            atr = (df['high'] - df['low']).mean() if len(df) > 0 else 0

            if diff < atr * 2:
                if lp.zone_type == ZoneType.LIQUIDITY_HIGH:
                    return "Price approaching buy-side liquidity - potential stop hunt above"
                elif lp.zone_type == ZoneType.LIQUIDITY_LOW:
                    return "Price approaching sell-side liquidity - potential stop hunt below"

        return None

    async def full_analysis(
        self,
        market_data: MarketData,
        include_mtf: bool = False,
        mtf_data: dict[str, MarketData] | None = None,
    ) -> FullAnalysis:
        """
        Perform complete technical analysis.

        Args:
            market_data: OHLCV data for primary timeframe
            include_mtf: Include multi-timeframe analysis
            mtf_data: Data for other timeframes (optional)
        """
        df = market_data.to_dataframe()

        # Calculate indicators
        indicators = self.calculate_indicators(df)

        # SMC analysis
        smc = self.analyze_smc(df, market_data.current_price)

        # Detect candle patterns
        patterns = self._detect_candle_patterns(df)

        # MTF analysis
        mtf_trend = {}
        if include_mtf and mtf_data:
            for tf, data in mtf_data.items():
                tf_df = data.to_dataframe()
                if not tf_df.empty:
                    trend, _ = self._detect_trend(tf_df)
                    mtf_trend[tf] = trend

        # Determine overall MTF bias
        mtf_bias = "neutral"
        if mtf_trend:
            bullish = sum(1 for t in mtf_trend.values() if t == TrendDirection.BULLISH)
            bearish = sum(1 for t in mtf_trend.values() if t == TrendDirection.BEARISH)
            if bullish > bearish:
                mtf_bias = "bullish"
            elif bearish > bullish:
                mtf_bias = "bearish"

        return FullAnalysis(
            symbol=market_data.symbol,
            timeframe=market_data.timeframe,
            current_price=market_data.current_price,
            timestamp=market_data.last_updated,
            indicators=indicators,
            candle_patterns=patterns,
            smc=smc,
            mtf_trend=mtf_trend,
            mtf_bias=mtf_bias,
        )

    def _detect_candle_patterns(self, df: pd.DataFrame) -> list[str]:
        """Detect common candlestick patterns."""
        patterns = []

        if len(df) < 3:
            return patterns

        open_p = df['open'].values
        close_p = df['close'].values
        high_p = df['high'].values
        low_p = df['low'].values

        # Last 3 candles
        for i in range(-3, 0):
            body = abs(close_p[i] - open_p[i])
            upper_wick = high_p[i] - max(open_p[i], close_p[i])
            lower_wick = min(open_p[i], close_p[i]) - low_p[i]
            total_range = high_p[i] - low_p[i]

            if total_range == 0:
                continue

            # Doji
            if body < total_range * 0.1:
                patterns.append("Doji (indecision)")

            # Hammer/Hanging Man
            if lower_wick > body * 2 and upper_wick < body * 0.5:
                if close_p[i] > open_p[i]:
                    patterns.append("Hammer (bullish reversal)")
                else:
                    patterns.append("Hanging Man (bearish reversal)")

            # Shooting Star/Inverted Hammer
            if upper_wick > body * 2 and lower_wick < body * 0.5:
                if close_p[i] < open_p[i]:
                    patterns.append("Shooting Star (bearish reversal)")
                else:
                    patterns.append("Inverted Hammer (bullish)")

            # Marubozu (strong momentum)
            if body > total_range * 0.9:
                if close_p[i] > open_p[i]:
                    patterns.append("Bullish Marubozu (strong buying)")
                else:
                    patterns.append("Bearish Marubozu (strong selling)")

        # Engulfing patterns
        if len(df) >= 2:
            prev_body = close_p[-2] - open_p[-2]
            curr_body = close_p[-1] - open_p[-1]

            if prev_body < 0 and curr_body > 0 and curr_body > abs(prev_body):
                patterns.append("Bullish Engulfing (reversal)")
            elif prev_body > 0 and curr_body < 0 and abs(curr_body) > prev_body:
                patterns.append("Bearish Engulfing (reversal)")

        return patterns[:5]  # Limit to 5 patterns


# Singleton
_ta_service: TechnicalAnalysisService | None = None


def get_technical_analysis_service() -> TechnicalAnalysisService:
    """Get or create TechnicalAnalysisService singleton."""
    global _ta_service
    if _ta_service is None:
        _ta_service = TechnicalAnalysisService()
    return _ta_service
