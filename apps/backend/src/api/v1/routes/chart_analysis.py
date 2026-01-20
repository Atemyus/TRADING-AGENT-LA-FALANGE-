"""
Chart Analysis API - Analyzes TradingView chart screenshots with AI Vision.

Returns: direction, confidence, SL, TP, BE (Break Even), TS (Trailing Stop)
"""

from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.engines.ai.vision_analyzer import get_vision_analyzer
import re


router = APIRouter(prefix="/ai", tags=["Chart Analysis"])


class ChartAnalysisRequest(BaseModel):
    symbol: str
    timeframes: List[str] = ["1H"]
    chart_image: str  # Base64
    request_sl_tp_be_ts: bool = True


class MultiTimeframeRequest(BaseModel):
    symbol: str
    chart_images: Dict[str, str]  # timeframe -> base64
    request_sl_tp_be_ts: bool = True


class TrailingStopConfig(BaseModel):
    enabled: bool
    activation_price: float
    trail_distance: float


class AnalysisResponse(BaseModel):
    direction: str
    confidence: float
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[List[float]]
    break_even_trigger: Optional[float]
    trailing_stop: Optional[TrailingStopConfig]
    risk_reward_ratio: Optional[float]
    reasoning: str
    patterns_detected: List[str]
    models_used: List[str]
    consensus_votes: Dict[str, str]


VISION_PROMPT = """Analyze this TradingView chart for {symbol} ({timeframes}).

Based on the chart, provide:

## DIRECTION
LONG, SHORT, or HOLD with confidence 0-100%

## ENTRY PRICE
Exact entry price level

## STOP LOSS (SL)
Price for stop loss based on visible support/resistance

## TAKE PROFIT (TP)
1-3 take profit levels

## BREAK EVEN (BE) TRIGGER
Price at which to move SL to entry (usually when TP1 hit)

## TRAILING STOP (TS)
- Should trailing stop be enabled?
- Activation price
- Trail distance in pips

## PATTERNS
Chart patterns you see

FORMAT YOUR RESPONSE:
DIRECTION: [LONG/SHORT/HOLD]
CONFIDENCE: [0-100]
ENTRY: [price]
STOP_LOSS: [price]
TAKE_PROFIT_1: [price]
TAKE_PROFIT_2: [price]
TAKE_PROFIT_3: [price]
BREAK_EVEN_TRIGGER: [price]
TRAILING_STOP_ENABLED: [yes/no]
TRAILING_STOP_ACTIVATION: [price]
TRAILING_STOP_DISTANCE: [pips]
PATTERNS: [pattern1, pattern2]
REASONING: [analysis]
"""


def parse_response(raw: str) -> Dict:
    result = {
        "direction": "HOLD",
        "confidence": 50,
        "entry_price": None,
        "stop_loss": None,
        "take_profit": [],
        "break_even_trigger": None,
        "trailing_stop": None,
        "patterns_detected": [],
        "reasoning": raw[:500],
    }

    lines = raw.upper().split("\n")

    for line in lines:
        line = line.strip()

        if line.startswith("DIRECTION:"):
            val = line.replace("DIRECTION:", "").strip()
            if "LONG" in val:
                result["direction"] = "LONG"
            elif "SHORT" in val:
                result["direction"] = "SHORT"

        elif line.startswith("CONFIDENCE:"):
            try:
                val = line.replace("CONFIDENCE:", "").strip().replace("%", "")
                result["confidence"] = min(100, max(0, float(val)))
            except:
                pass

        elif line.startswith("ENTRY:"):
            try:
                result["entry_price"] = float(line.replace("ENTRY:", "").strip())
            except:
                pass

        elif line.startswith("STOP_LOSS:"):
            try:
                result["stop_loss"] = float(line.replace("STOP_LOSS:", "").strip())
            except:
                pass

        elif line.startswith("TAKE_PROFIT_1:"):
            try:
                result["take_profit"].append(float(line.replace("TAKE_PROFIT_1:", "").strip()))
            except:
                pass

        elif line.startswith("TAKE_PROFIT_2:"):
            try:
                result["take_profit"].append(float(line.replace("TAKE_PROFIT_2:", "").strip()))
            except:
                pass

        elif line.startswith("TAKE_PROFIT_3:"):
            try:
                result["take_profit"].append(float(line.replace("TAKE_PROFIT_3:", "").strip()))
            except:
                pass

        elif line.startswith("BREAK_EVEN_TRIGGER:"):
            try:
                result["break_even_trigger"] = float(line.replace("BREAK_EVEN_TRIGGER:", "").strip())
            except:
                pass

        elif line.startswith("TRAILING_STOP_ENABLED:"):
            if "YES" in line:
                result["trailing_stop"] = {"enabled": True, "activation_price": 0, "trail_distance": 0}

        elif line.startswith("TRAILING_STOP_ACTIVATION:") and result.get("trailing_stop"):
            try:
                result["trailing_stop"]["activation_price"] = float(line.replace("TRAILING_STOP_ACTIVATION:", "").strip())
            except:
                pass

        elif line.startswith("TRAILING_STOP_DISTANCE:") and result.get("trailing_stop"):
            try:
                result["trailing_stop"]["trail_distance"] = float(line.replace("TRAILING_STOP_DISTANCE:", "").strip())
            except:
                pass

        elif line.startswith("PATTERNS:"):
            val = line.replace("PATTERNS:", "").strip()
            result["patterns_detected"] = [p.strip() for p in val.split(",") if p.strip()]

    return result


@router.post("/analyze-chart", response_model=AnalysisResponse)
async def analyze_chart(request: ChartAnalysisRequest):
    """Analyze TradingView chart screenshot with AI Vision models."""
    analyzer = get_vision_analyzer()

    prompt = VISION_PROMPT.format(
        symbol=request.symbol,
        timeframes=", ".join(request.timeframes)
    )

    images = {"main": request.chart_image}

    try:
        results = await analyzer.analyze_all_models(images, prompt)

        votes = {}
        all_parsed = []

        for r in results:
            if not r.error and r.raw_response:
                parsed = parse_response(r.raw_response)
                all_parsed.append(parsed)
                votes[r.model] = parsed["direction"]

        if not all_parsed:
            raise HTTPException(status_code=500, detail="All AI models failed")

        # Consensus
        counts = {"LONG": 0, "SHORT": 0, "HOLD": 0}
        for p in all_parsed:
            counts[p["direction"]] += 1

        consensus_dir = max(counts, key=counts.get)
        agreeing = [p for p in all_parsed if p["direction"] == consensus_dir]

        avg_conf = sum(p["confidence"] for p in agreeing) / len(agreeing)

        entry_prices = [p["entry_price"] for p in agreeing if p["entry_price"]]
        stop_losses = [p["stop_loss"] for p in agreeing if p["stop_loss"]]
        take_profits = []
        for p in agreeing:
            take_profits.extend(p.get("take_profit", []))
        be_triggers = [p["break_even_trigger"] for p in agreeing if p["break_even_trigger"]]

        ts = None
        for p in agreeing:
            if p.get("trailing_stop") and p["trailing_stop"].get("enabled"):
                ts = TrailingStopConfig(
                    enabled=True,
                    activation_price=p["trailing_stop"].get("activation_price", 0),
                    trail_distance=p["trailing_stop"].get("trail_distance", 10),
                )
                break

        patterns = []
        for p in agreeing:
            patterns.extend(p.get("patterns_detected", []))

        return AnalysisResponse(
            direction=consensus_dir,
            confidence=round(avg_conf, 1),
            entry_price=sum(entry_prices) / len(entry_prices) if entry_prices else None,
            stop_loss=sum(stop_losses) / len(stop_losses) if stop_losses else None,
            take_profit=sorted(set(take_profits))[:3] if take_profits else None,
            break_even_trigger=sum(be_triggers) / len(be_triggers) if be_triggers else None,
            trailing_stop=ts,
            risk_reward_ratio=None,
            reasoning=agreeing[0].get("reasoning", ""),
            patterns_detected=list(set(patterns)),
            models_used=[r.model for r in results if not r.error],
            consensus_votes=votes,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-multi-timeframe")
async def analyze_multi_timeframe(request: MultiTimeframeRequest):
    """Analyze multiple TradingView chart screenshots (different timeframes)."""
    analyzer = get_vision_analyzer()

    timeframes = list(request.chart_images.keys())
    prompt = VISION_PROMPT.format(
        symbol=request.symbol,
        timeframes=", ".join(timeframes)
    )

    try:
        results = await analyzer.analyze_all_models(request.chart_images, prompt)

        votes = {}
        all_parsed = []

        for r in results:
            if not r.error and r.raw_response:
                parsed = parse_response(r.raw_response)
                all_parsed.append(parsed)
                votes[r.model] = parsed["direction"]

        if not all_parsed:
            raise HTTPException(status_code=500, detail="All AI models failed")

        counts = {"LONG": 0, "SHORT": 0, "HOLD": 0}
        for p in all_parsed:
            counts[p["direction"]] += 1

        consensus_dir = max(counts, key=counts.get)
        agreeing = [p for p in all_parsed if p["direction"] == consensus_dir]

        avg_conf = sum(p["confidence"] for p in agreeing) / len(agreeing)

        entry_prices = [p["entry_price"] for p in agreeing if p["entry_price"]]
        stop_losses = [p["stop_loss"] for p in agreeing if p["stop_loss"]]
        take_profits = []
        for p in agreeing:
            take_profits.extend(p.get("take_profit", []))

        return {
            "direction": consensus_dir,
            "confidence": round(avg_conf, 1),
            "entry_price": sum(entry_prices) / len(entry_prices) if entry_prices else None,
            "stop_loss": sum(stop_losses) / len(stop_losses) if stop_losses else None,
            "take_profit": sorted(set(take_profits))[:3] if take_profits else None,
            "models_used": [r.model for r in results if not r.error],
            "consensus_votes": votes,
            "timeframes_analyzed": timeframes,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
