"""
Chart Generator Service - Creates chart images with customizable indicators.

This service generates professional trading charts with:
- Candlestick/OHLC data
- Technical indicators (RSI, MACD, MAs, Bollinger Bands, etc.)
- SMC annotations (Order Blocks, FVG, Liquidity zones)
- Support/Resistance levels

Each AI model can request specific indicators for their analysis.
"""

import base64
import io
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Chart generation with matplotlib
import matplotlib
import pandas as pd

matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from src.services.market_data_service import MarketDataService, get_market_data_service
from src.services.technical_analysis_service import (
    TechnicalAnalysisService,
    get_technical_analysis_service,
)


@dataclass
class IndicatorConfig:
    """Configuration for an indicator to display on chart."""
    name: str
    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)
    color: str = "#00ff88"
    panel: str = "main"  # "main", "rsi", "macd", "volume"


@dataclass
class ChartConfig:
    """Configuration for chart generation."""
    symbol: str
    timeframe: str = "15m"
    bars: int = 100
    width: int = 1200
    height: int = 800
    theme: str = "dark"

    # Indicators to display
    indicators: list[IndicatorConfig] = field(default_factory=list)

    # SMC annotations
    show_order_blocks: bool = True
    show_fvg: bool = True
    show_liquidity: bool = True
    show_structure: bool = True  # BOS/CHoCH

    # Support/Resistance
    show_sr_levels: bool = True

    # Volume
    show_volume: bool = True


# Predefined indicator sets for different analysis styles
INDICATOR_PRESETS = {
    "momentum": [
        IndicatorConfig("RSI", True, {"period": 14}, "#ff6b6b", "rsi"),
        IndicatorConfig("MACD", True, {"fast": 12, "slow": 26, "signal": 9}, "#4ecdc4", "macd"),
        IndicatorConfig("EMA", True, {"period": 9}, "#ffd93d", "main"),
        IndicatorConfig("EMA", True, {"period": 21}, "#6bcb77", "main"),
    ],
    "trend": [
        IndicatorConfig("EMA", True, {"period": 20}, "#ffd93d", "main"),
        IndicatorConfig("EMA", True, {"period": 50}, "#6bcb77", "main"),
        IndicatorConfig("EMA", True, {"period": 200}, "#ff6b6b", "main"),
        IndicatorConfig("ADX", True, {"period": 14}, "#4ecdc4", "adx"),
    ],
    "volatility": [
        IndicatorConfig("Bollinger", True, {"period": 20, "std": 2}, "#9b59b6", "main"),
        IndicatorConfig("ATR", True, {"period": 14}, "#e74c3c", "atr"),
        IndicatorConfig("Keltner", True, {"period": 20, "atr_mult": 1.5}, "#3498db", "main"),
    ],
    "smc": [
        IndicatorConfig("EMA", True, {"period": 50}, "#6bcb77", "main"),
        IndicatorConfig("Volume", True, {}, "#ffffff", "volume"),
        # SMC elements are drawn separately
    ],
    "complete": [
        IndicatorConfig("RSI", True, {"period": 14}, "#ff6b6b", "rsi"),
        IndicatorConfig("MACD", True, {"fast": 12, "slow": 26, "signal": 9}, "#4ecdc4", "macd"),
        IndicatorConfig("EMA", True, {"period": 20}, "#ffd93d", "main"),
        IndicatorConfig("EMA", True, {"period": 50}, "#6bcb77", "main"),
        IndicatorConfig("EMA", True, {"period": 200}, "#ff6b6b", "main"),
        IndicatorConfig("Bollinger", True, {"period": 20, "std": 2}, "#9b59b6", "main"),
        IndicatorConfig("Volume", True, {}, "#ffffff", "volume"),
    ],
}


class ChartGeneratorService:
    """
    Generates chart images with technical indicators and SMC analysis.
    """

    def __init__(self):
        self.market_data: MarketDataService = None
        self.ta_service: TechnicalAnalysisService = None
        self._initialized = False

        # Theme colors
        self.themes = {
            "dark": {
                "bg": "#0d1117",
                "grid": "#21262d",
                "text": "#c9d1d9",
                "candle_up": "#00ff88",
                "candle_down": "#ff4757",
                "volume_up": "#00ff8844",
                "volume_down": "#ff475744",
            },
            "light": {
                "bg": "#ffffff",
                "grid": "#e1e4e8",
                "text": "#24292e",
                "candle_up": "#22c55e",
                "candle_down": "#ef4444",
                "volume_up": "#22c55e44",
                "volume_down": "#ef444444",
            }
        }

    async def initialize(self):
        """Initialize services."""
        if self._initialized:
            return
        self.market_data = get_market_data_service()
        self.ta_service = get_technical_analysis_service()
        self._initialized = True

    async def generate_chart(
        self,
        config: ChartConfig,
        indicator_preset: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """
        Generate a chart image with specified configuration.

        Args:
            config: Chart configuration
            indicator_preset: Optional preset name ("momentum", "trend", "smc", etc.)

        Returns:
            Tuple of (base64 image, metadata dict)
        """
        await self.initialize()

        # Apply preset if specified
        if indicator_preset and indicator_preset in INDICATOR_PRESETS:
            config.indicators = INDICATOR_PRESETS[indicator_preset]

        # Fetch market data
        market_data = await self.market_data.get_market_data(
            config.symbol,
            config.timeframe,
            config.bars
        )

        if not market_data or not market_data.candles:
            raise ValueError(f"No market data available for {config.symbol}")

        # Calculate technical analysis
        analysis = await self.ta_service.full_analysis(market_data, include_mtf=False)

        # Create the chart
        theme = self.themes.get(config.theme, self.themes["dark"])

        # Determine subplot layout based on indicators
        panels = self._get_panel_layout(config)

        fig, axes = plt.subplots(
            len(panels), 1,
            figsize=(config.width/100, config.height/100),
            gridspec_kw={'height_ratios': [3] + [1]*(len(panels)-1)},
            facecolor=theme["bg"]
        )

        if len(panels) == 1:
            axes = [axes]

        # Style all axes
        for ax in axes:
            ax.set_facecolor(theme["bg"])
            ax.tick_params(colors=theme["text"])
            ax.spines['bottom'].set_color(theme["grid"])
            ax.spines['top'].set_color(theme["grid"])
            ax.spines['left'].set_color(theme["grid"])
            ax.spines['right'].set_color(theme["grid"])
            ax.grid(True, color=theme["grid"], alpha=0.3)

        # Prepare OHLC data for plotting
        df = self._candles_to_dataframe(market_data.candles)

        # Draw candlesticks on main panel
        main_ax = axes[0]
        self._draw_candlesticks(main_ax, df, theme)

        # Draw indicators on appropriate panels
        panel_axes = {panels[i]: axes[i] for i in range(len(panels))}
        self._draw_indicators(panel_axes, df, config.indicators, analysis, theme)

        # Draw SMC elements if enabled
        if config.show_order_blocks or config.show_fvg or config.show_liquidity:
            self._draw_smc(main_ax, df, analysis.smc, config, theme)

        # Draw structure (BOS/CHoCH) if enabled
        if config.show_structure:
            self._draw_structure(main_ax, df, analysis.smc, theme)

        # Draw S/R levels
        if config.show_sr_levels:
            self._draw_sr_levels(main_ax, df, analysis.smc, theme)

        # Draw volume if enabled
        if config.show_volume and "volume" in panel_axes:
            self._draw_volume(panel_axes["volume"], df, theme)

        # Set title
        main_ax.set_title(
            f"{config.symbol} - {config.timeframe}",
            color=theme["text"],
            fontsize=14,
            fontweight='bold'
        )

        # Format x-axis with dates
        main_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

        plt.tight_layout()

        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', facecolor=theme["bg"], edgecolor='none', dpi=100)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close(fig)

        # Build metadata
        metadata = {
            "symbol": config.symbol,
            "timeframe": config.timeframe,
            "bars": len(df),
            "current_price": float(market_data.current_price),
            "indicators_shown": [ind.name for ind in config.indicators if ind.enabled],
            "smc_enabled": {
                "order_blocks": config.show_order_blocks,
                "fvg": config.show_fvg,
                "liquidity": config.show_liquidity,
                "structure": config.show_structure,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        return image_base64, metadata

    async def generate_multi_indicator_charts(
        self,
        symbol: str,
        timeframe: str = "15m",
        bars: int = 100,
    ) -> dict[str, tuple[str, dict[str, Any]]]:
        """
        Generate multiple chart images with different indicator sets.
        This allows each AI to see charts with different perspectives.

        Returns:
            Dict mapping preset name to (base64 image, metadata)
        """
        results = {}

        for preset_name in ["momentum", "trend", "smc", "complete"]:
            config = ChartConfig(
                symbol=symbol,
                timeframe=timeframe,
                bars=bars,
                indicators=INDICATOR_PRESETS[preset_name],
                show_order_blocks=(preset_name in ["smc", "complete"]),
                show_fvg=(preset_name in ["smc", "complete"]),
                show_liquidity=(preset_name in ["smc", "complete"]),
                show_structure=(preset_name in ["smc", "complete"]),
            )

            try:
                image, metadata = await self.generate_chart(config, preset_name)
                results[preset_name] = (image, metadata)
            except Exception as e:
                print(f"Failed to generate {preset_name} chart: {e}")

        return results

    def _get_panel_layout(self, config: ChartConfig) -> list[str]:
        """Determine which panels are needed based on indicators."""
        panels = ["main"]

        for ind in config.indicators:
            if ind.enabled and ind.panel not in panels:
                panels.append(ind.panel)

        if config.show_volume and "volume" not in panels:
            panels.append("volume")

        return panels

    def _candles_to_dataframe(self, candles: list) -> pd.DataFrame:
        """Convert candles to DataFrame."""
        data = []
        for c in candles:
            data.append({
                'timestamp': c.timestamp,
                'open': float(c.open),
                'high': float(c.high),
                'low': float(c.low),
                'close': float(c.close),
                'volume': float(c.volume) if c.volume else 0,
            })

        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        return df

    def _draw_candlesticks(self, ax, df: pd.DataFrame, theme: dict):
        """Draw candlestick chart."""
        for idx, (timestamp, row) in enumerate(df.iterrows()):
            color = theme["candle_up"] if row['close'] >= row['open'] else theme["candle_down"]

            # Wick
            ax.plot([idx, idx], [row['low'], row['high']], color=color, linewidth=1)

            # Body
            body_bottom = min(row['open'], row['close'])
            body_height = abs(row['close'] - row['open'])
            rect = Rectangle(
                (idx - 0.4, body_bottom),
                0.8,
                body_height or 0.0001,  # Avoid zero height
                facecolor=color,
                edgecolor=color
            )
            ax.add_patch(rect)

        ax.set_xlim(-1, len(df))
        ax.set_ylim(df['low'].min() * 0.999, df['high'].max() * 1.001)

    def _draw_indicators(
        self,
        panel_axes: dict[str, plt.Axes],
        df: pd.DataFrame,
        indicators: list[IndicatorConfig],
        analysis,
        theme: dict
    ):
        """Draw indicators on appropriate panels."""
        main_ax = panel_axes.get("main")

        for ind in indicators:
            if not ind.enabled:
                continue

            ax = panel_axes.get(ind.panel)
            if not ax:
                continue

            if ind.name == "EMA":
                period = ind.params.get("period", 20)
                ema = df['close'].ewm(span=period).mean()
                ax.plot(range(len(df)), ema, color=ind.color, linewidth=1,
                       label=f"EMA {period}", alpha=0.8)

            elif ind.name == "SMA":
                period = ind.params.get("period", 20)
                sma = df['close'].rolling(period).mean()
                ax.plot(range(len(df)), sma, color=ind.color, linewidth=1,
                       label=f"SMA {period}", alpha=0.8)

            elif ind.name == "RSI":
                period = ind.params.get("period", 14)
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))

                ax.plot(range(len(df)), rsi, color=ind.color, linewidth=1.5)
                ax.axhline(y=70, color='#ff6b6b', linestyle='--', alpha=0.5)
                ax.axhline(y=30, color='#6bcb77', linestyle='--', alpha=0.5)
                ax.axhline(y=50, color=theme["text"], linestyle='--', alpha=0.3)
                ax.set_ylim(0, 100)
                ax.set_ylabel("RSI", color=theme["text"])

            elif ind.name == "MACD":
                fast = ind.params.get("fast", 12)
                slow = ind.params.get("slow", 26)
                signal_period = ind.params.get("signal", 9)

                ema_fast = df['close'].ewm(span=fast).mean()
                ema_slow = df['close'].ewm(span=slow).mean()
                macd_line = ema_fast - ema_slow
                signal_line = macd_line.ewm(span=signal_period).mean()
                histogram = macd_line - signal_line

                ax.plot(range(len(df)), macd_line, color='#3498db', linewidth=1, label='MACD')
                ax.plot(range(len(df)), signal_line, color='#e74c3c', linewidth=1, label='Signal')

                colors = ['#6bcb77' if h >= 0 else '#ff6b6b' for h in histogram]
                ax.bar(range(len(df)), histogram, color=colors, alpha=0.5, width=0.8)
                ax.axhline(y=0, color=theme["text"], linestyle='-', alpha=0.3)
                ax.set_ylabel("MACD", color=theme["text"])

            elif ind.name == "Bollinger":
                period = ind.params.get("period", 20)
                std_mult = ind.params.get("std", 2)

                sma = df['close'].rolling(period).mean()
                std = df['close'].rolling(period).std()
                upper = sma + (std * std_mult)
                lower = sma - (std * std_mult)

                ax.plot(range(len(df)), sma, color=ind.color, linewidth=1, alpha=0.8)
                ax.plot(range(len(df)), upper, color=ind.color, linewidth=0.5, alpha=0.5)
                ax.plot(range(len(df)), lower, color=ind.color, linewidth=0.5, alpha=0.5)
                ax.fill_between(range(len(df)), lower, upper, color=ind.color, alpha=0.1)

        # Add legend to main panel
        if main_ax:
            main_ax.legend(loc='upper left', facecolor=theme["bg"],
                          edgecolor=theme["grid"], labelcolor=theme["text"])

    def _draw_smc(self, ax, df: pd.DataFrame, smc_analysis, config: ChartConfig, theme: dict):
        """Draw Smart Money Concepts on the chart."""
        if not smc_analysis:
            return

        # Order Blocks
        if config.show_order_blocks and hasattr(smc_analysis, 'order_blocks'):
            for ob in smc_analysis.order_blocks[:5]:  # Limit to recent 5
                if ob.type == "bullish":
                    color = "#00ff8844"
                    edge = "#00ff88"
                else:
                    color = "#ff475744"
                    edge = "#ff4757"

                # Find index for the order block
                rect = Rectangle(
                    (len(df) - 20, ob.zone_low),
                    20,
                    ob.zone_high - ob.zone_low,
                    facecolor=color,
                    edgecolor=edge,
                    linewidth=1,
                    linestyle='--'
                )
                ax.add_patch(rect)
                ax.annotate(
                    f"OB {'↑' if ob.type == 'bullish' else '↓'}",
                    xy=(len(df) - 10, ob.zone_high),
                    color=edge,
                    fontsize=8
                )

        # Fair Value Gaps
        if config.show_fvg and hasattr(smc_analysis, 'fvg_zones'):
            for fvg in smc_analysis.fvg_zones[:5]:
                color = "#ffd93d44" if fvg.type == "bullish" else "#9b59b644"
                edge = "#ffd93d" if fvg.type == "bullish" else "#9b59b6"

                rect = Rectangle(
                    (len(df) - 15, fvg.gap_low),
                    15,
                    fvg.gap_high - fvg.gap_low,
                    facecolor=color,
                    edgecolor=edge,
                    linewidth=1
                )
                ax.add_patch(rect)
                ax.annotate(
                    "FVG",
                    xy=(len(df) - 7, (fvg.gap_high + fvg.gap_low) / 2),
                    color=edge,
                    fontsize=7
                )

        # Liquidity zones
        if config.show_liquidity and hasattr(smc_analysis, 'liquidity_zones'):
            for liq in smc_analysis.liquidity_zones[:3]:
                ax.axhline(
                    y=liq.price_level,
                    color='#e74c3c',
                    linestyle=':',
                    alpha=0.6,
                    linewidth=1
                )
                ax.annotate(
                    f"LIQ ${liq.price_level:.5f}",
                    xy=(len(df) - 5, liq.price_level),
                    color='#e74c3c',
                    fontsize=7
                )

    def _draw_structure(self, ax, df: pd.DataFrame, smc_analysis, theme: dict):
        """Draw market structure (BOS/CHoCH) on the chart."""
        if not smc_analysis or not hasattr(smc_analysis, 'structure'):
            return

        structure = smc_analysis.structure

        # Draw swing highs and lows
        if hasattr(structure, 'swing_highs'):
            for sh in structure.swing_highs[-5:]:
                ax.annotate('HH' if sh.is_higher else 'LH',
                           xy=(len(df) - 10, sh.price),
                           color='#ffd93d', fontsize=8)

        if hasattr(structure, 'swing_lows'):
            for sl in structure.swing_lows[-5:]:
                ax.annotate('HL' if sl.is_higher else 'LL',
                           xy=(len(df) - 10, sl.price),
                           color='#3498db', fontsize=8)

    def _draw_sr_levels(self, ax, df: pd.DataFrame, smc_analysis, theme: dict):
        """Draw support and resistance levels."""
        if not smc_analysis:
            return

        # Support levels
        if hasattr(smc_analysis, 'supply_demand') and smc_analysis.supply_demand:
            for zone in smc_analysis.supply_demand[:3]:
                if zone.type == "demand":
                    ax.axhspan(
                        zone.zone_low, zone.zone_high,
                        alpha=0.1, color='#00ff88',
                        label='Demand Zone'
                    )
                else:
                    ax.axhspan(
                        zone.zone_low, zone.zone_high,
                        alpha=0.1, color='#ff4757',
                        label='Supply Zone'
                    )

    def _draw_volume(self, ax, df: pd.DataFrame, theme: dict):
        """Draw volume bars."""
        colors = [
            theme["volume_up"] if df['close'].iloc[i] >= df['open'].iloc[i]
            else theme["volume_down"]
            for i in range(len(df))
        ]
        ax.bar(range(len(df)), df['volume'], color=colors, width=0.8)
        ax.set_ylabel("Volume", color=theme["text"])
        ax.set_xlim(-1, len(df))


# Singleton instance
_chart_generator: ChartGeneratorService | None = None


def get_chart_generator_service() -> ChartGeneratorService:
    """Get or create the chart generator singleton."""
    global _chart_generator
    if _chart_generator is None:
        _chart_generator = ChartGeneratorService()
    return _chart_generator
