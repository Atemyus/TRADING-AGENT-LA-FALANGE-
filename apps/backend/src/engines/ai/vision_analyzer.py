"""
Vision Analyzer - Multi-AI visual chart analysis via AIML API.

Uses AIML API gateway to access AI models:
- ChatGPT 5.2 (vision-capable)
- Gemini 3 Pro (vision-capable)
- Grok 4.1 Fast (vision-capable)
- Qwen3 VL (vision-capable)
- Llama 4 Scout (text analysis)
"""

import asyncio
import json
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

import httpx

from src.core.config import settings


class VisionModel(str, Enum):
    """Available AI models via AIML API."""
    # AIML API model IDs (updated 2026-01-27)
    CHATGPT_5_2 = "openai/gpt-5-2"
    GEMINI_3_PRO = "google/gemini-3-pro-preview"
    GROK_4_1 = "x-ai/grok-4-1-fast-reasoning"
    QWEN3_VL = "alibaba/qwen3-vl-32b-instruct"  # Vision-Language model
    LLAMA_4_SCOUT = "meta-llama/llama-4-scout"  # Text analysis


# Human-readable model names for display
MODEL_DISPLAY_NAMES = {
    VisionModel.CHATGPT_5_2: "ChatGPT 5.2",
    VisionModel.GEMINI_3_PRO: "Gemini 3 Pro",
    VisionModel.GROK_4_1: "Grok 4.1 Fast",
    VisionModel.QWEN3_VL: "Qwen3 VL",
    VisionModel.LLAMA_4_SCOUT: "Llama 4 Scout",
}


@dataclass
class VisionAnalysisResult:
    """Result from a single vision AI analysis."""
    model: str
    model_display_name: str
    direction: str  # LONG, SHORT, HOLD
    confidence: float  # 0-100
    entry_zone: Optional[Dict[str, float]] = None  # {"min": x, "max": y}
    stop_loss: Optional[float] = None
    take_profit: Optional[List[float]] = None
    break_even_trigger: Optional[float] = None  # Price to move SL to entry
    trailing_stop: Optional[Dict[str, Any]] = None  # {"enabled": bool, "distance_pips": x}
    risk_reward: Optional[float] = None
    patterns_detected: Optional[List[str]] = None
    trend_analysis: Optional[Dict[str, str]] = None  # per timeframe
    key_levels: Optional[Dict[str, List[float]]] = None  # support/resistance
    reasoning: Optional[str] = None
    raw_response: Optional[str] = None
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class VisionAnalyzer:
    """
    Analyzes chart images using multiple vision-capable AI models via AIML API.
    """

    SYSTEM_PROMPT = """You are an elite institutional trader and technical analyst specializing in forex, indices, commodities, and crypto.
You are looking at a TradingView chart screenshot. Analyze EVERYTHING visible on the chart.

## WHAT TO ANALYZE ON THE CHART

### 1. VISIBLE INDICATORS (Read their values from the chart)
- Moving Averages (EMA/SMA): Note crossovers, price position relative to MAs
- RSI: Overbought (>70), Oversold (<30), divergences
- MACD: Signal line crossovers, histogram momentum
- Bollinger Bands: Squeeze, breakouts, band walks
- Stochastic: %K/%D crossovers, overbought/oversold
- Volume: Confirm moves with volume spikes
- Any other indicators visible on the chart

### 2. SMART MONEY CONCEPTS (SMC)
- Order Blocks: Bullish OB (last red candle before up move), Bearish OB (last green candle before down move)
- Fair Value Gaps (FVG/Imbalance): Gaps between candle wicks that price may fill
- Break of Structure (BOS): When price breaks previous swing high/low
- Change of Character (CHoCH): First sign of trend reversal
- Liquidity Pools: Equal highs/lows, trendlines, stop hunt zones
- Premium/Discount Zones: Price above/below 50% of range

### 3. PRICE ACTION & PATTERNS
- Candlestick patterns (engulfing, pin bars, doji, etc.)
- Chart patterns (triangles, channels, head & shoulders, etc.)
- Support and resistance levels
- Trend structure (HH/HL for uptrend, LH/LL for downtrend)

## RESPONSE FORMAT (MUST FOLLOW EXACTLY)

**DIRECTION**: [LONG/SHORT/HOLD]
**CONFIDENCE**: [0-100]%
**ENTRY_ZONE**: [price_min] - [price_max]
**STOP_LOSS**: [price]
**TAKE_PROFIT_1**: [price]
**TAKE_PROFIT_2**: [price] (optional)
**TAKE_PROFIT_3**: [price] (optional)
**BREAK_EVEN_TRIGGER**: [price] (move SL to entry when price reaches this level)
**TRAILING_STOP**: [YES/NO], [distance in pips if YES]
**RISK_REWARD**: [ratio like 1:2 or 1:3]

**KEY_LEVELS**:
- Support: [price1], [price2]
- Resistance: [price1], [price2]

**INDICATORS_ANALYSIS**:
- [List each visible indicator and its current reading/signal]

**SMC_ANALYSIS**:
- Order Blocks: [locations if visible]
- FVG/Imbalance: [any gaps to fill]
- Structure: [BOS/CHoCH if any]
- Liquidity: [where stops may be hunted]

**PATTERNS_DETECTED**: [list patterns found]

**TREND_ANALYSIS**:
- Short-term: [BULLISH/BEARISH/NEUTRAL]
- Medium-term: [BULLISH/BEARISH/NEUTRAL]
- Long-term: [BULLISH/BEARISH/NEUTRAL]

**REASONING**: [Your institutional-grade analysis explaining why this trade setup makes sense]

IMPORTANT: Be PRECISE with price levels. Read them directly from the chart. Reference specific indicator values and SMC zones you can see."""

    def __init__(self):
        self.api_key = settings.AIML_API_KEY
        self.base_url = settings.AIML_BASE_URL
        self.timeout = 90.0  # Vision models may need more time

    async def analyze_with_model(
        self,
        model: VisionModel,
        images_base64: Dict[str, str],
        prompt: str,
    ) -> VisionAnalysisResult:
        """Analyze charts using a specific model via AIML API."""
        display_name = MODEL_DISPLAY_NAMES.get(model, model.value)

        if not self.api_key:
            return VisionAnalysisResult(
                model=model.value,
                model_display_name=display_name,
                direction="HOLD",
                confidence=0,
                error="AIML API key not configured"
            )

        start_time = datetime.now()

        try:
            # Build content with images (OpenAI-compatible format)
            content = []
            for timeframe, image_b64 in images_base64.items():
                content.append({
                    "type": "text",
                    "text": f"📊 Chart for {timeframe} timeframe:"
                })
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_b64}",
                        "detail": "high"
                    }
                })

            content.append({"type": "text", "text": prompt})

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
                                "role": "system",
                                "content": self.SYSTEM_PROMPT
                            },
                            {
                                "role": "user",
                                "content": content
                            }
                        ],
                        "max_tokens": 2500,
                        "temperature": 0.2
                    }
                )
                response.raise_for_status()
                data = response.json()

            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            raw_text = data["choices"][0]["message"]["content"]

            return self._parse_analysis_response(
                raw_text=raw_text,
                model=model,
                latency_ms=latency
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", error_msg)
            except:
                pass
            return VisionAnalysisResult(
                model=model.value,
                model_display_name=display_name,
                direction="HOLD",
                confidence=0,
                error=f"{display_name}: {error_msg}"
            )
        except Exception as e:
            return VisionAnalysisResult(
                model=model.value,
                model_display_name=display_name,
                direction="HOLD",
                confidence=0,
                error=f"{display_name}: {str(e)}"
            )

    async def analyze_all_models(
        self,
        images_base64: Dict[str, str],
        prompt: str,
        models: Optional[List[VisionModel]] = None,
        max_models: int = 6,
    ) -> List[VisionAnalysisResult]:
        """
        Run analysis on all specified vision models in parallel via AIML API.

        Args:
            images_base64: Dict mapping timeframe to base64 chart image
            prompt: Analysis prompt
            models: List of models to use. Defaults to all 8 models.
            max_models: Maximum number of models to use (for faster modes)

        Returns:
            List of analysis results from each model
        """
        if models is None:
            models = list(VisionModel)

        # Limit models based on max_models parameter
        if max_models < len(models):
            models = models[:max_models]

        # Run all models in parallel
        tasks = [
            self.analyze_with_model(model, images_base64, prompt)
            for model in models
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                display_name = MODEL_DISPLAY_NAMES.get(models[i], models[i].value)
                processed_results.append(VisionAnalysisResult(
                    model=models[i].value,
                    model_display_name=display_name,
                    direction="HOLD",
                    confidence=0,
                    error=str(result)
                ))
            else:
                processed_results.append(result)

        return processed_results

    def _parse_analysis_response(
        self,
        raw_text: str,
        model: VisionModel,
        latency_ms: int
    ) -> VisionAnalysisResult:
        """Parse the AI response to extract structured data."""
        display_name = MODEL_DISPLAY_NAMES.get(model, model.value)

        result = VisionAnalysisResult(
            model=model.value,
            model_display_name=display_name,
            direction="HOLD",
            confidence=50,
            raw_response=raw_text,
            latency_ms=latency_ms
        )

        text_upper = raw_text.upper()

        # Extract direction
        direction_patterns = [
            r'\*\*DIRECTION\*\*:\s*(LONG|SHORT|HOLD)',
            r'DIRECTION:\s*(LONG|SHORT|HOLD)',
            r'DIRECTION\s*[:\-]\s*(LONG|SHORT|HOLD)',
        ]
        for pattern in direction_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                result.direction = match.group(1).upper()
                break

        # Fallback: check for BUY/SELL keywords
        if result.direction == "HOLD":
            if "RECOMMENDATION" in text_upper:
                section = text_upper.split("RECOMMENDATION")[1][:200]
                if "LONG" in section or "BUY" in section:
                    result.direction = "LONG"
                elif "SHORT" in section or "SELL" in section:
                    result.direction = "SHORT"

        # Extract confidence
        confidence_patterns = [
            r'\*\*CONFIDENCE\*\*:\s*(\d+)',
            r'CONFIDENCE:\s*(\d+)',
            r'CONFIDENCE\s*[:\-]\s*(\d+)',
            r'(\d+)\s*%\s*CONFIDENCE',
        ]
        for pattern in confidence_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                result.confidence = min(100, max(0, int(match.group(1))))
                break

        # Extract stop loss
        sl_patterns = [
            r'\*\*STOP_LOSS\*\*:\s*[\$€]?([\d.]+)',
            r'STOP_LOSS:\s*[\$€]?([\d.]+)',
            r'STOP\s*LOSS[:\s]*[\$€]?([\d.]+)',
            r'SL[:\s]*[\$€]?([\d.]+)',
        ]
        for pattern in sl_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                try:
                    result.stop_loss = float(match.group(1))
                    break
                except ValueError:
                    pass

        # Extract take profit levels
        tp_patterns = [
            r'TAKE_PROFIT_?(\d)?[:\s]*[\$€]?([\d.]+)',
            r'TP_?(\d)?[:\s]*[\$€]?([\d.]+)',
            r'TARGET_?(\d)?[:\s]*[\$€]?([\d.]+)',
        ]
        take_profits = []
        for pattern in tp_patterns:
            matches = re.findall(pattern, raw_text, re.IGNORECASE)
            for m in matches:
                try:
                    tp_value = float(m[1]) if isinstance(m, tuple) else float(m)
                    if tp_value not in take_profits:
                        take_profits.append(tp_value)
                except (ValueError, IndexError):
                    pass
        if take_profits:
            result.take_profit = sorted(take_profits)[:3]  # Max 3 targets

        # Extract break even trigger
        be_patterns = [
            r'BREAK_EVEN_TRIGGER[:\s]*[\$€]?([\d.]+)',
            r'BE_TRIGGER[:\s]*[\$€]?([\d.]+)',
            r'BREAK\s*EVEN[:\s]*[\$€]?([\d.]+)',
        ]
        for pattern in be_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                try:
                    result.break_even_trigger = float(match.group(1))
                    break
                except ValueError:
                    pass

        # Extract trailing stop config
        ts_patterns = [
            r'TRAILING_STOP[:\s]*(YES|NO)(?:[,\s]*(\d+))?',
            r'TRAILING\s*STOP[:\s]*(YES|NO|ENABLED|DISABLED)(?:[,\s]*(\d+))?',
        ]
        for pattern in ts_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                enabled = match.group(1).upper() in ["YES", "ENABLED"]
                distance = None
                if match.group(2):
                    try:
                        distance = int(match.group(2))
                    except ValueError:
                        pass
                result.trailing_stop = {
                    "enabled": enabled,
                    "distance_pips": distance or 20  # Default 20 pips
                }
                break

        # Extract risk/reward
        rr_patterns = [
            r'RISK_REWARD[:\s]*[\d.]*[:\s]*([\d.]+)',
            r'RISK[/\s]*REWARD[:\s]*(\d+)[:\s]*(\d+)',
            r'R[:\s]*R[:\s]*([\d.]+)',
            r'(\d+)[:\s]*(\d+)\s*(?:R|RR)',
        ]
        for pattern in rr_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) >= 2 and groups[1]:
                        result.risk_reward = float(groups[1]) / float(groups[0]) if float(groups[0]) > 0 else None
                    else:
                        result.risk_reward = float(groups[0])
                    break
                except (ValueError, ZeroDivisionError):
                    pass

        # Extract key levels (support/resistance)
        support_match = re.search(r'Support[:\s]*([\d.,\s]+)', raw_text, re.IGNORECASE)
        resistance_match = re.search(r'Resistance[:\s]*([\d.,\s]+)', raw_text, re.IGNORECASE)

        key_levels = {}
        if support_match:
            supports = re.findall(r'([\d.]+)', support_match.group(1))
            key_levels["support"] = [float(s) for s in supports[:3]]
        if resistance_match:
            resistances = re.findall(r'([\d.]+)', resistance_match.group(1))
            key_levels["resistance"] = [float(r) for r in resistances[:3]]
        if key_levels:
            result.key_levels = key_levels

        # Extract patterns detected
        pattern_keywords = [
            "head and shoulders", "inverse head and shoulders",
            "double top", "double bottom", "triple top", "triple bottom",
            "ascending triangle", "descending triangle", "symmetrical triangle",
            "bull flag", "bear flag", "pennant", "wedge",
            "rising wedge", "falling wedge", "channel",
            "cup and handle", "rounding bottom", "rounding top",
            "engulfing", "doji", "hammer", "inverted hammer",
            "shooting star", "morning star", "evening star",
            "three white soldiers", "three black crows",
            "harami", "piercing line", "dark cloud cover",
            "support", "resistance", "breakout", "breakdown",
            "golden cross", "death cross", "divergence"
        ]
        detected = []
        text_lower = raw_text.lower()
        for p in pattern_keywords:
            if p.lower() in text_lower:
                detected.append(p.title())
        result.patterns_detected = detected if detected else None

        # Extract trend analysis
        trend_analysis = {}
        trend_patterns = [
            (r'short[\s\-]*term[:\s]*(BULLISH|BEARISH|NEUTRAL)', 'short_term'),
            (r'medium[\s\-]*term[:\s]*(BULLISH|BEARISH|NEUTRAL)', 'medium_term'),
            (r'long[\s\-]*term[:\s]*(BULLISH|BEARISH|NEUTRAL)', 'long_term'),
        ]
        for pattern, key in trend_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                trend_analysis[key] = match.group(1).upper()
        if trend_analysis:
            result.trend_analysis = trend_analysis

        # Extract entry zone
        entry_patterns = [
            r'ENTRY_ZONE[:\s]*([\d.]+)\s*[-–]\s*([\d.]+)',
            r'ENTRY[:\s]*([\d.]+)\s*[-–]\s*([\d.]+)',
        ]
        for pattern in entry_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                try:
                    result.entry_zone = {
                        "min": float(match.group(1)),
                        "max": float(match.group(2))
                    }
                    break
                except ValueError:
                    pass

        # Extract reasoning (first meaningful paragraph)
        reasoning_match = re.search(r'\*\*REASONING\*\*[:\s]*(.+?)(?:\n\n|\*\*|$)', raw_text, re.DOTALL | re.IGNORECASE)
        if reasoning_match:
            result.reasoning = reasoning_match.group(1).strip()[:500]
        else:
            # Fallback: use last paragraph
            paragraphs = [p.strip() for p in raw_text.split('\n\n') if p.strip()]
            if paragraphs:
                result.reasoning = paragraphs[-1][:500]

        return result

    def calculate_consensus(
        self,
        results: List[VisionAnalysisResult]
    ) -> Dict[str, Any]:
        """
        Calculate consensus from multiple AI analysis results.

        With 8 models, requires at least 5 to agree for a strong signal.
        """
        valid_results = [r for r in results if not r.error and r.direction != "HOLD"]
        total_results = len([r for r in results if not r.error])

        if not valid_results:
            return {
                "consensus_direction": "HOLD",
                "consensus_confidence": 0,
                "models_agree": 0,
                "total_models": total_results,
                "agreement_ratio": 0,
                "is_strong_signal": False,
                "avg_stop_loss": None,
                "avg_take_profit": None,
                "avg_break_even_trigger": None,
                "trailing_stop_consensus": None,
                "individual_results": results
            }

        # Count votes
        long_votes = [r for r in valid_results if r.direction == "LONG"]
        short_votes = [r for r in valid_results if r.direction == "SHORT"]

        # Determine majority direction
        if len(long_votes) > len(short_votes):
            consensus_direction = "LONG"
            agreeing_results = long_votes
        elif len(short_votes) > len(long_votes):
            consensus_direction = "SHORT"
            agreeing_results = short_votes
        else:
            # Tie - use confidence as tiebreaker
            long_confidence = sum(r.confidence for r in long_votes) / len(long_votes) if long_votes else 0
            short_confidence = sum(r.confidence for r in short_votes) / len(short_votes) if short_votes else 0

            if long_confidence > short_confidence:
                consensus_direction = "LONG"
                agreeing_results = long_votes
            elif short_confidence > long_confidence:
                consensus_direction = "SHORT"
                agreeing_results = short_votes
            else:
                return {
                    "consensus_direction": "HOLD",
                    "consensus_confidence": 0,
                    "models_agree": 0,
                    "total_models": total_results,
                    "agreement_ratio": 0,
                    "is_strong_signal": False,
                    "avg_stop_loss": None,
                    "avg_take_profit": None,
                    "avg_break_even_trigger": None,
                    "trailing_stop_consensus": None,
                    "individual_results": results
                }

        # Calculate averages from agreeing models
        models_agree = len(agreeing_results)
        agreement_ratio = models_agree / total_results if total_results > 0 else 0

        avg_confidence = sum(r.confidence for r in agreeing_results) / models_agree

        # Average SL
        stop_losses = [r.stop_loss for r in agreeing_results if r.stop_loss]
        avg_sl = sum(stop_losses) / len(stop_losses) if stop_losses else None

        # Average TP (first target)
        take_profits = [r.take_profit[0] for r in agreeing_results if r.take_profit]
        avg_tp = sum(take_profits) / len(take_profits) if take_profits else None

        # Average BE trigger
        be_triggers = [r.break_even_trigger for r in agreeing_results if r.break_even_trigger]
        avg_be = sum(be_triggers) / len(be_triggers) if be_triggers else None

        # Trailing stop consensus (majority vote)
        ts_votes = [r.trailing_stop for r in agreeing_results if r.trailing_stop]
        ts_enabled_count = sum(1 for ts in ts_votes if ts.get("enabled"))
        ts_consensus = None
        if ts_votes:
            ts_consensus = {
                "enabled": ts_enabled_count > len(ts_votes) / 2,
                "distance_pips": int(sum(ts.get("distance_pips", 20) for ts in ts_votes) / len(ts_votes))
            }

        # Strong signal requires 4+ models agreeing (out of 6) with 70%+ confidence
        is_strong_signal = models_agree >= 4 and avg_confidence >= 70

        return {
            "consensus_direction": consensus_direction,
            "consensus_confidence": round(avg_confidence, 1),
            "models_agree": models_agree,
            "total_models": total_results,
            "agreement_ratio": round(agreement_ratio, 2),
            "is_strong_signal": is_strong_signal,
            "avg_stop_loss": round(avg_sl, 5) if avg_sl else None,
            "avg_take_profit": round(avg_tp, 5) if avg_tp else None,
            "avg_break_even_trigger": round(avg_be, 5) if avg_be else None,
            "trailing_stop_consensus": ts_consensus,
            "voting_breakdown": {
                "LONG": len(long_votes),
                "SHORT": len(short_votes),
                "HOLD": total_results - len(long_votes) - len(short_votes)
            },
            "model_votes": {
                r.model_display_name: {
                    "direction": r.direction,
                    "confidence": r.confidence,
                    "latency_ms": r.latency_ms
                } for r in results if not r.error
            },
            "individual_results": results
        }


# Singleton instance
_vision_analyzer: Optional[VisionAnalyzer] = None


def get_vision_analyzer() -> VisionAnalyzer:
    """Get or create the vision analyzer singleton."""
    global _vision_analyzer
    if _vision_analyzer is None:
        _vision_analyzer = VisionAnalyzer()
    return _vision_analyzer
