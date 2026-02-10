"""
Autonomous AI Analyst - Each AI independently chooses its analysis approach.

This system:
1. Provides each AI with raw market data
2. Each AI decides which indicators/tools to use
3. AI requests specific chart views with chosen indicators
4. AI performs its own SMC and technical analysis
5. Returns a comprehensive, independently-reasoned analysis
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

from src.core.config import settings
from src.services.chart_generator_service import (
    ChartConfig,
    ChartGeneratorService,
    get_chart_generator_service,
)
from src.services.market_data_service import MarketDataService, get_market_data_service
from src.services.technical_analysis_service import (
    TechnicalAnalysisService,
    get_technical_analysis_service,
)


class AIModel(str, Enum):
    """Available AI models for autonomous analysis."""
    # AIML API model IDs (updated 2026-01-27)
    CHATGPT_5_2 = "openai/gpt-5-2"
    GEMINI_3_PRO = "google/gemini-3-pro-preview"
    GROK_4_1 = "x-ai/grok-4-1-fast-reasoning"
    QWEN3_VL = "alibaba/qwen3-vl-32b-instruct"  # Vision-Language model
    LLAMA_4_SCOUT = "meta-llama/llama-4-scout"  # Text analysis
    ERNIE_4_5_VL = "baidu/ernie-4.5-vl-424b-a47b"  # Vision-Language model


MODEL_DISPLAY_NAMES = {
    AIModel.CHATGPT_5_2: "ChatGPT 5.2",
    AIModel.GEMINI_3_PRO: "Gemini 3 Pro",
    AIModel.GROK_4_1: "Grok 4.1 Fast",
    AIModel.QWEN3_VL: "Qwen3 VL",
    AIModel.LLAMA_4_SCOUT: "Llama 4 Scout",
    AIModel.ERNIE_4_5_VL: "ERNIE 4.5 VL",
}


@dataclass
class AutonomousAnalysisResult:
    """Result from an autonomous AI analysis."""
    model: str
    model_display_name: str

    # Trading decision
    direction: str  # LONG, SHORT, HOLD
    confidence: float  # 0-100

    # Trade parameters
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: list[float] = field(default_factory=list)
    risk_reward: float | None = None

    # Advanced trade management
    break_even_trigger: float | None = None  # Price at which to move SL to entry
    trailing_stop_pips: float | None = None  # Trailing stop distance in pips
    partial_tp_percent: float | None = None  # Percentage to close at TP1 (e.g., 50%)

    # AI's chosen analysis approach
    indicators_used: list[str] = field(default_factory=list)
    analysis_style: str = ""  # "momentum", "smc", "trend", etc.

    # Detailed analysis
    market_structure: str | None = None
    trend_analysis: dict[str, str] = field(default_factory=dict)
    smc_analysis: str | None = None
    indicator_readings: dict[str, str] = field(default_factory=dict)
    patterns_found: list[str] = field(default_factory=list)
    key_levels: dict[str, list[float]] = field(default_factory=dict)

    # Full reasoning
    reasoning: str = ""

    # Metadata
    latency_ms: int = 0
    error: str | None = None


# System prompt that gives AI full autonomy
AUTONOMOUS_SYSTEM_PROMPT = """You are an elite institutional trader with complete autonomy to analyze markets using ANY strategy or indicators you prefer.

## YOUR TASK
Analyze the provided market data and chart for {symbol} ({timeframe}).

## YOUR AUTONOMY
You have FULL FREEDOM to choose:
1. **Your Trading Style**: Scalping, Day Trading, Swing Trading, Position Trading
2. **Your Analysis Method**: Technical Analysis, Smart Money Concepts (SMC), Price Action, Indicator-Based, or ANY combination
3. **Which Indicators to Focus On**: You can use any visible indicators or request mental calculations
4. **Advanced Tools**: Fibonacci, Pitchfork, Pivot Points (Standard, Fibonacci, Camarilla, Woodie)

## AVAILABLE TOOLS & DATA

### Raw Market Data Provided:
{market_data}

### Pre-Calculated Indicators:
{indicators}
- VWAP (Volume Weighted Average Price)
- EMA (9, 21, 50, 200)
- RSI (7, 14)
- MACD, Stochastic, ADX, ATR
- Bollinger Bands

### Smart Money Concepts (SMC) Analysis:
{smc_data}
- Order Blocks (OB)
- Fair Value Gaps (FVG)
- Liquidity Pools
- Market Structure (BOS/CHoCH)
- Smart Money Traps (Inducement) - Bull Traps, Bear Traps, Stop Hunts

### Fibonacci Levels:
Automatically calculated retracement (23.6%, 38.2%, 50%, 61.8%, 78.6%) and extension levels (127.2%, 161.8%, 200%, 261.8%)

### Pivot Points:
- Standard (PP, R1-R3, S1-S3)
- Fibonacci Pivots
- Camarilla Pivots
- Woodie Pivots

### Chart Image:
The chart shows {chart_description}

## YOUR ANALYSIS PROCESS

1. **Choose Your Approach**: Decide which style suits this market condition
2. **Analyze Structure**: Identify trend, key levels, market phase
3. **Apply Your Methods**: Use indicators, SMC, or pure price action as YOU see fit
4. **Form Your Opinion**: Make an independent trading decision
5. **Define Risk**: Set precise entry, SL, TP based on YOUR analysis

## RESPONSE FORMAT (MUST FOLLOW)

```json
{{
  "analysis_style": "[Your chosen style: momentum/trend/smc/price_action/hybrid]",
  "indicators_used": ["List of indicators you focused on"],

  "market_structure": {{
    "trend": "[Bullish/Bearish/Ranging]",
    "phase": "[Accumulation/Markup/Distribution/Markdown]",
    "key_observation": "[Your main structural observation]"
  }},

  "technical_analysis": {{
    "indicator_readings": {{
      "RSI": "[Your reading and interpretation]",
      "MACD": "[Your reading and interpretation]",
      "Moving_Averages": "[Your reading and interpretation]",
      "[Other]": "[As needed]"
    }},
    "patterns": ["List any patterns you identified"]
  }},

  "smc_analysis": {{
    "order_blocks": "[Your OB analysis if relevant]",
    "fair_value_gaps": "[FVG analysis if relevant]",
    "liquidity": "[Liquidity analysis if relevant]",
    "structure_breaks": "[BOS/CHoCH if relevant]"
  }},

  "key_levels": {{
    "support": [price1, price2],
    "resistance": [price1, price2],
    "poi": [prices of interest]
  }},

  "trade_decision": {{
    "direction": "[LONG/SHORT/HOLD]",
    "confidence": [0-100],
    "entry_price": [exact price],
    "stop_loss": [exact price],
    "take_profit_1": [price],
    "take_profit_2": [price],
    "take_profit_3": [price],
    "risk_reward": [ratio like 2.5],
    "break_even_trigger": [price at which to move SL to entry, null if not recommended],
    "trailing_stop_pips": [trailing stop distance in pips, null if not recommended],
    "partial_close_at_tp1": [percentage to close at TP1, e.g. 50, null if full position]
  }},

  "reasoning": "[Your complete analysis narrative - explain WHY you see what you see, WHY you chose this approach, and WHY this trade makes sense. Be specific with prices and levels.]"
}}
```

IMPORTANT:
- Be PRECISE with price levels
- Express YOUR unique perspective
- If you see no trade, say HOLD with reasoning
- Reference specific data points from the provided information
- SCRIVI TUTTO IN ITALIANO: Tutta l'analisi, il reasoning, le osservazioni e le descrizioni devono essere scritte ESCLUSIVAMENTE in lingua italiana. Non usare inglese.
"""


class AutonomousAnalyst:
    """
    Manages autonomous AI analysis where each model independently
    decides its analysis approach and indicators.
    """

    def __init__(self):
        self.api_key = settings.AIML_API_KEY
        self.base_url = settings.AIML_BASE_URL
        self.timeout = 120.0  # Longer timeout for complex analysis

        self.chart_generator: ChartGeneratorService = None
        self.market_data: MarketDataService = None
        self.ta_service: TechnicalAnalysisService = None
        self._initialized = False

    async def initialize(self):
        """Initialize services."""
        if self._initialized:
            return

        self.chart_generator = get_chart_generator_service()
        self.market_data = get_market_data_service()
        self.ta_service = get_technical_analysis_service()
        self._initialized = True

    async def analyze_with_model(
        self,
        model: AIModel,
        symbol: str,
        timeframe: str = "15m",
        chart_preset: str = "complete",
        prefetched_data: Any | None = None,
    ) -> AutonomousAnalysisResult:
        """
        Run autonomous analysis with a single AI model.

        The AI receives:
        - Raw OHLCV data
        - Pre-calculated indicators
        - SMC analysis
        - Chart image with chosen preset

        The AI then independently decides how to analyze and trade.
        """
        await self.initialize()
        display_name = MODEL_DISPLAY_NAMES.get(model, model.value)

        if not self.api_key:
            print(f"[AutonomousAnalyst] ⚠️ AIML API KEY NOT SET - No real API call for {model.value}. Set AIML_API_KEY env variable.")
            return AutonomousAnalysisResult(
                model=model.value,
                model_display_name=display_name,
                direction="HOLD",
                confidence=0,
                error="⚠️ AIML API KEY NON CONFIGURATA - Nessuna chiamata API reale. Configura AIML_API_KEY nelle variabili d'ambiente."
            )

        start_time = datetime.now()

        try:
            # 1. Fetch market data (use prefetched if available to avoid rate limits)
            market_data = prefetched_data
            if market_data is None:
                market_data = await self.market_data.get_market_data(symbol, timeframe, 100)

            if not market_data or not market_data.candles:
                return AutonomousAnalysisResult(
                    model=model.value,
                    model_display_name=display_name,
                    direction="HOLD",
                    confidence=0,
                    error=f"No market data for {symbol}"
                )

            # 2. Calculate technical analysis
            analysis = await self.ta_service.full_analysis(market_data, include_mtf=False)

            # 3. Generate chart with the preset
            chart_config = ChartConfig(
                symbol=symbol,
                timeframe=timeframe,
                bars=100,
                show_order_blocks=True,
                show_fvg=True,
                show_liquidity=True,
                show_structure=True,
                show_volume=True,
            )
            chart_image, chart_meta = await self.chart_generator.generate_chart(
                chart_config, chart_preset
            )

            # 4. Format data for the AI
            market_data_text = self._format_market_data(market_data)
            indicators_text = self._format_indicators(analysis.indicators)
            smc_text = self._format_smc(analysis.smc)
            chart_description = f"Candlestick chart with {', '.join(chart_meta.get('indicators_shown', []))}"

            # 5. Build the prompt
            prompt = AUTONOMOUS_SYSTEM_PROMPT.format(
                symbol=symbol,
                timeframe=timeframe,
                market_data=market_data_text,
                indicators=indicators_text,
                smc_data=smc_text,
                chart_description=chart_description,
            )

            # 6. Call the AI with vision
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model.value,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": prompt
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{chart_image}",
                                            "detail": "high"
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 4000,
                        "temperature": 0.3
                    }
                )
                response.raise_for_status()
                data = response.json()

            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            raw_text = data["choices"][0]["message"]["content"]

            # 7. Parse the response
            return self._parse_response(raw_text, model, latency)

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", error_msg)
            except:
                pass
            return AutonomousAnalysisResult(
                model=model.value,
                model_display_name=display_name,
                direction="HOLD",
                confidence=0,
                error=f"{display_name}: {error_msg}"
            )
        except Exception as e:
            return AutonomousAnalysisResult(
                model=model.value,
                model_display_name=display_name,
                direction="HOLD",
                confidence=0,
                error=f"{display_name}: {str(e)}"
            )

    async def analyze_all_models(
        self,
        symbol: str,
        timeframe: str = "15m",
        models: list[AIModel] | None = None,
    ) -> list[AutonomousAnalysisResult]:
        """
        Run autonomous analysis with all AI models in parallel.
        Each model independently decides its analysis approach.
        """
        await self.initialize()

        if models is None:
            models = list(AIModel)

        # Pre-fetch market data UNA SOLA VOLTA per evitare rate limiting Yahoo (429)
        prefetched_data = None
        try:
            prefetched_data = await self.market_data.get_market_data(symbol, timeframe, 100)
            if prefetched_data and prefetched_data.candles:
                print(f"[AutonomousAnalyst] Pre-fetched {len(prefetched_data.candles)} candles for {symbol}/{timeframe}")
            else:
                print(f"[AutonomousAnalyst] ⚠️ No candle data for {symbol}/{timeframe}")
        except Exception as e:
            print(f"[AutonomousAnalyst] ⚠️ Failed to pre-fetch market data for {symbol}: {e}")

        # Each model gets a different chart preset for diverse perspectives
        presets = ["momentum", "trend", "smc", "complete", "volatility", "smc"]

        tasks = [
            self.analyze_with_model(
                model,
                symbol,
                timeframe,
                presets[i % len(presets)],
                prefetched_data=prefetched_data,
            )
            for i, model in enumerate(models)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                display_name = MODEL_DISPLAY_NAMES.get(models[i], models[i].value)
                processed.append(AutonomousAnalysisResult(
                    model=models[i].value,
                    model_display_name=display_name,
                    direction="HOLD",
                    confidence=0,
                    error=str(result)
                ))
            else:
                processed.append(result)

        return processed

    def calculate_consensus(
        self,
        results: list[AutonomousAnalysisResult]
    ) -> dict[str, Any]:
        """
        Calculate consensus from autonomous AI analyses.
        Respects each AI's independent analysis while finding common ground.
        """
        valid = [r for r in results if not r.error and r.direction != "HOLD"]
        total = len([r for r in results if not r.error])

        if not valid:
            return {
                "direction": "HOLD",
                "confidence": 0,
                "consensus_strength": 0,
                "models_agree": 0,
                "total_models": total,
                "individual_analyses": results,
            }

        # Count votes
        long_votes = [r for r in valid if r.direction == "LONG"]
        short_votes = [r for r in valid if r.direction == "SHORT"]

        if len(long_votes) > len(short_votes):
            direction = "LONG"
            agreeing = long_votes
        elif len(short_votes) > len(long_votes):
            direction = "SHORT"
            agreeing = short_votes
        else:
            # Tie - use confidence
            long_conf = sum(r.confidence for r in long_votes) / len(long_votes) if long_votes else 0
            short_conf = sum(r.confidence for r in short_votes) / len(short_votes) if short_votes else 0
            if long_conf >= short_conf:
                direction = "LONG"
                agreeing = long_votes
            else:
                direction = "SHORT"
                agreeing = short_votes

        models_agree = len(agreeing)
        avg_confidence = sum(r.confidence for r in agreeing) / models_agree
        consensus_strength = models_agree / total if total > 0 else 0

        # Average trade parameters
        stop_losses = [r.stop_loss for r in agreeing if r.stop_loss]
        take_profits = [r.take_profit[0] for r in agreeing if r.take_profit]
        entries = [r.entry_price for r in agreeing if r.entry_price]

        # Advanced management parameters
        break_evens = [r.break_even_trigger for r in agreeing if r.break_even_trigger]
        trailing_stops = [r.trailing_stop_pips for r in agreeing if r.trailing_stop_pips]
        partial_tps = [r.partial_tp_percent for r in agreeing if r.partial_tp_percent]

        # Collect unique analysis approaches
        styles_used = list(set(r.analysis_style for r in agreeing if r.analysis_style))
        all_indicators = []
        for r in agreeing:
            all_indicators.extend(r.indicators_used)
        unique_indicators = list(set(all_indicators))

        return {
            "direction": direction,
            "confidence": round(avg_confidence, 1),
            "consensus_strength": round(consensus_strength, 2),
            "models_agree": models_agree,
            "total_models": total,
            "is_strong_signal": models_agree >= 4 and avg_confidence >= 70,

            # Aggregated trade parameters
            "entry_price": round(sum(entries) / len(entries), 5) if entries else None,
            "stop_loss": round(sum(stop_losses) / len(stop_losses), 5) if stop_losses else None,
            "take_profit": round(sum(take_profits) / len(take_profits), 5) if take_profits else None,

            # Advanced trade management
            "break_even_trigger": round(sum(break_evens) / len(break_evens), 5) if break_evens else None,
            "trailing_stop_pips": round(sum(trailing_stops) / len(trailing_stops), 1) if trailing_stops else None,
            "partial_tp_percent": round(sum(partial_tps) / len(partial_tps), 0) if partial_tps else None,

            # Analysis diversity
            "analysis_styles_used": styles_used,
            "indicators_considered": unique_indicators,

            # Individual analyses for transparency
            "individual_analyses": results,

            # Voting breakdown
            "vote_breakdown": {
                "LONG": len(long_votes),
                "SHORT": len(short_votes),
                "HOLD": total - len(long_votes) - len(short_votes),
            }
        }

    def _format_market_data(self, market_data) -> str:
        """Format market data for AI consumption."""
        candles = market_data.candles[-20:]  # Last 20 candles
        lines = [
            f"Current Price: {market_data.current_price}",
            f"Symbol: {market_data.symbol}",
            f"Timeframe: {market_data.timeframe}",
            "",
            "Recent OHLCV (last 20 candles):",
        ]

        for c in candles:
            lines.append(
                f"  {c.timestamp}: O={c.open} H={c.high} L={c.low} C={c.close} V={c.volume or 0}"
            )

        return "\n".join(lines)

    def _format_indicators(self, indicators) -> str:
        """Format indicator values for AI consumption."""
        if not indicators:
            return "No indicators calculated"

        lines = []

        if hasattr(indicators, 'rsi') and indicators.rsi:
            lines.append(f"RSI(14): {indicators.rsi:.2f}")
        if hasattr(indicators, 'macd') and indicators.macd:
            lines.append(f"MACD: {indicators.macd:.5f}")
        if hasattr(indicators, 'macd_signal') and indicators.macd_signal:
            lines.append(f"MACD Signal: {indicators.macd_signal:.5f}")
        if hasattr(indicators, 'macd_histogram') and indicators.macd_histogram:
            lines.append(f"MACD Histogram: {indicators.macd_histogram:.5f}")
        if hasattr(indicators, 'ema_20') and indicators.ema_20:
            lines.append(f"EMA 20: {indicators.ema_20:.5f}")
        if hasattr(indicators, 'ema_50') and indicators.ema_50:
            lines.append(f"EMA 50: {indicators.ema_50:.5f}")
        if hasattr(indicators, 'ema_200') and indicators.ema_200:
            lines.append(f"EMA 200: {indicators.ema_200:.5f}")
        if hasattr(indicators, 'bb_upper') and indicators.bb_upper:
            lines.append(f"Bollinger Upper: {indicators.bb_upper:.5f}")
        if hasattr(indicators, 'bb_lower') and indicators.bb_lower:
            lines.append(f"Bollinger Lower: {indicators.bb_lower:.5f}")
        if hasattr(indicators, 'adx') and indicators.adx:
            lines.append(f"ADX: {indicators.adx:.2f}")
        if hasattr(indicators, 'atr') and indicators.atr:
            lines.append(f"ATR: {indicators.atr:.5f}")
        if hasattr(indicators, 'stoch_k') and indicators.stoch_k:
            lines.append(f"Stochastic %K: {indicators.stoch_k:.2f}")
        if hasattr(indicators, 'stoch_d') and indicators.stoch_d:
            lines.append(f"Stochastic %D: {indicators.stoch_d:.2f}")

        return "\n".join(lines) if lines else "No indicators calculated"

    def _format_smc(self, smc) -> str:
        """Format SMC analysis for AI consumption."""
        if not smc:
            return "No SMC analysis available"

        lines = []

        # Market Structure
        if hasattr(smc, 'structure') and smc.structure:
            s = smc.structure
            if hasattr(s, 'trend'):
                lines.append(f"Trend: {s.trend}")
            if hasattr(s, 'last_bos'):
                lines.append(f"Last BOS: {s.last_bos}")
            if hasattr(s, 'last_choch'):
                lines.append(f"Last CHoCH: {s.last_choch}")

        # Order Blocks
        if hasattr(smc, 'order_blocks') and smc.order_blocks:
            lines.append("\nOrder Blocks:")
            for ob in smc.order_blocks[:3]:
                lines.append(f"  {ob.type.upper()} OB: {ob.zone_low:.5f} - {ob.zone_high:.5f}")

        # FVG
        if hasattr(smc, 'fvg_zones') and smc.fvg_zones:
            lines.append("\nFair Value Gaps:")
            for fvg in smc.fvg_zones[:3]:
                lines.append(f"  {fvg.type.upper()} FVG: {fvg.gap_low:.5f} - {fvg.gap_high:.5f}")

        # Liquidity
        if hasattr(smc, 'liquidity_zones') and smc.liquidity_zones:
            lines.append("\nLiquidity Zones:")
            for liq in smc.liquidity_zones[:3]:
                lines.append(f"  {liq.type}: {liq.price_level:.5f}")

        # Supply/Demand
        if hasattr(smc, 'supply_demand') and smc.supply_demand:
            lines.append("\nSupply/Demand Zones:")
            for zone in smc.supply_demand[:3]:
                lines.append(f"  {zone.type.upper()}: {zone.zone_low:.5f} - {zone.zone_high:.5f}")

        # Fibonacci Levels
        if hasattr(smc, 'fibonacci') and smc.fibonacci:
            fib = smc.fibonacci
            lines.append("\nFibonacci Levels:")
            lines.append(f"  Swing: {fib.swing_low:.5f} → {fib.swing_high:.5f} ({fib.direction})")
            lines.append(f"  Retracements: 38.2%={fib.retracement_382:.5f}, 50%={fib.retracement_500:.5f}, 61.8%={fib.retracement_618:.5f}")
            lines.append(f"  Extensions: 127.2%={fib.extension_1272:.5f}, 161.8%={fib.extension_1618:.5f}")

        # Smart Money Traps
        if hasattr(smc, 'smart_money_traps') and smc.smart_money_traps:
            lines.append("\nSmart Money Traps (Inducement):")
            for trap in smc.smart_money_traps[:3]:
                lines.append(f"  {trap.trap_type.upper()}: {trap.price_level:.5f} - {trap.description}")

        # Pivot Points
        if hasattr(smc, 'pivot_points') and smc.pivot_points:
            lines.append("\nPivot Points:")
            pp = smc.pivot_points
            if 'PP' in pp:
                lines.append(f"  Standard: PP={pp.get('PP', 0):.5f}, R1={pp.get('R1', 0):.5f}, S1={pp.get('S1', 0):.5f}")
            if 'Fib_PP' in pp:
                lines.append(f"  Fibonacci: PP={pp.get('Fib_PP', 0):.5f}, R1={pp.get('Fib_R1', 0):.5f}, S1={pp.get('Fib_S1', 0):.5f}")
            if 'Cam_R3' in pp:
                lines.append(f"  Camarilla: R3={pp.get('Cam_R3', 0):.5f}, S3={pp.get('Cam_S3', 0):.5f}")

        return "\n".join(lines) if lines else "No SMC analysis available"

    def _parse_response(
        self,
        raw_text: str,
        model: AIModel,
        latency_ms: int
    ) -> AutonomousAnalysisResult:
        """Parse the AI's autonomous analysis response."""
        display_name = MODEL_DISPLAY_NAMES.get(model, model.value)

        result = AutonomousAnalysisResult(
            model=model.value,
            model_display_name=display_name,
            direction="HOLD",
            confidence=50,
            latency_ms=latency_ms,
        )

        try:
            # Try to extract JSON from the response
            json_match = raw_text.find('{')
            json_end = raw_text.rfind('}') + 1

            if json_match != -1 and json_end > json_match:
                json_str = raw_text[json_match:json_end]
                data = json.loads(json_str)

                # Analysis style
                result.analysis_style = data.get("analysis_style", "")
                result.indicators_used = data.get("indicators_used", [])

                # Trade decision
                trade = data.get("trade_decision", {})
                result.direction = trade.get("direction", "HOLD").upper()
                result.confidence = float(trade.get("confidence", 50))
                result.entry_price = trade.get("entry_price")
                result.stop_loss = trade.get("stop_loss")

                tps = []
                for i in range(1, 4):
                    tp = trade.get(f"take_profit_{i}")
                    if tp:
                        tps.append(float(tp))
                result.take_profit = tps

                result.risk_reward = trade.get("risk_reward")

                # Advanced trade management
                if trade.get("break_even_trigger"):
                    result.break_even_trigger = float(trade["break_even_trigger"])
                if trade.get("trailing_stop_pips"):
                    result.trailing_stop_pips = float(trade["trailing_stop_pips"])
                if trade.get("partial_close_at_tp1"):
                    result.partial_tp_percent = float(trade["partial_close_at_tp1"])

                # Market structure
                ms = data.get("market_structure", {})
                if ms:
                    result.market_structure = f"{ms.get('trend', '')} - {ms.get('phase', '')}. {ms.get('key_observation', '')}"
                    result.trend_analysis = {
                        "trend": ms.get("trend", ""),
                        "phase": ms.get("phase", ""),
                    }

                # Technical analysis
                ta = data.get("technical_analysis", {})
                result.indicator_readings = ta.get("indicator_readings", {})
                result.patterns_found = ta.get("patterns", [])

                # SMC
                smc = data.get("smc_analysis", {})
                if smc:
                    smc_parts = []
                    for key, value in smc.items():
                        if value:
                            smc_parts.append(f"{key}: {value}")
                    result.smc_analysis = " | ".join(smc_parts)

                # Key levels
                result.key_levels = data.get("key_levels", {})

                # Reasoning
                result.reasoning = data.get("reasoning", "")

        except json.JSONDecodeError:
            # Fallback: extract key info from text
            result.reasoning = raw_text[:1000]

            # Try basic extraction
            if "LONG" in raw_text.upper():
                result.direction = "LONG"
            elif "SHORT" in raw_text.upper():
                result.direction = "SHORT"

        return result


# Singleton instance
_autonomous_analyst: AutonomousAnalyst | None = None


def get_autonomous_analyst() -> AutonomousAnalyst:
    """Get or create the autonomous analyst singleton."""
    global _autonomous_analyst
    if _autonomous_analyst is None:
        _autonomous_analyst = AutonomousAnalyst()
    return _autonomous_analyst
