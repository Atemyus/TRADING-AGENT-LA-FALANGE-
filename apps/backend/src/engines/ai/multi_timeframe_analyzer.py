"""
Multi-Timeframe Analyzer - Combines numeric and visual AI analysis.

This analyzer:
1. Collects market data across multiple timeframes
2. Generates chart images for each timeframe
3. Runs both numeric (text) and visual analysis in parallel
4. Combines results using a consensus voting system
"""

import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.engines.ai.chart_vision import get_chart_vision_service, ChartVisionService
from src.engines.ai.vision_analyzer import get_vision_analyzer, VisionAnalyzer, VisionAnalysisResult
from src.engines.ai.consensus_engine import ConsensusEngine, VotingMethod
from src.services.ai_service import AIService
from src.core.config import settings


class AnalysisMode(str, Enum):
    """Analysis depth modes."""
    QUICK = "quick"          # Only fastest models, single timeframe
    STANDARD = "standard"    # All text models, 2 timeframes
    PREMIUM = "premium"      # All models + vision, 3 timeframes
    ULTRA = "ultra"          # Everything + more timeframes


@dataclass
class TimeframeAnalysis:
    """Analysis result for a single timeframe."""
    timeframe: str
    direction: str
    confidence: float
    indicators: Dict[str, Any]
    patterns: List[str]
    support_levels: List[float]
    resistance_levels: List[float]


@dataclass
class MultiTimeframeResult:
    """Complete multi-timeframe analysis result."""
    symbol: str
    timestamp: datetime
    mode: AnalysisMode

    # Final consensus
    final_direction: str  # LONG, SHORT, HOLD
    final_confidence: float

    # Trade parameters
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[List[float]] = None
    position_size_percent: Optional[float] = None
    risk_reward_ratio: Optional[float] = None

    # Per-timeframe analysis
    timeframe_analyses: Dict[str, TimeframeAnalysis] = field(default_factory=dict)

    # Individual model votes
    text_model_votes: List[Dict[str, Any]] = field(default_factory=list)
    vision_model_votes: List[Dict[str, Any]] = field(default_factory=list)

    # Confluence score (how aligned are the timeframes)
    confluence_score: float = 0.0

    # Metadata
    total_models_used: int = 0
    total_latency_ms: int = 0
    errors: List[str] = field(default_factory=list)


class MultiTimeframeAnalyzer:
    """
    Analyzes assets across multiple timeframes using both text and vision AI.
    """

    # Mode configurations
    MODE_CONFIG = {
        AnalysisMode.QUICK: {
            "timeframes": ["1H"],
            "use_vision": False,
            "text_models": ["groq"],  # Fastest
        },
        AnalysisMode.STANDARD: {
            "timeframes": ["15m", "1H"],
            "use_vision": False,
            "text_models": ["groq", "openai", "anthropic"],
        },
        AnalysisMode.PREMIUM: {
            "timeframes": ["15m", "1H", "4H"],
            "use_vision": True,
            "text_models": ["groq", "openai", "anthropic", "gemini"],
        },
        AnalysisMode.ULTRA: {
            "timeframes": ["5m", "15m", "1H", "4H", "1D"],
            "use_vision": True,
            "text_models": ["groq", "openai", "anthropic", "gemini", "mistral"],
        },
    }

    def __init__(self):
        self.chart_service: ChartVisionService = None
        self.vision_analyzer: VisionAnalyzer = None
        self.ai_service: AIService = None
        self.consensus_engine = ConsensusEngine()
        self._initialized = False

    async def initialize(self):
        """Initialize services lazily."""
        if self._initialized:
            return

        try:
            self.chart_service = get_chart_vision_service()
        except ImportError as e:
            print(f"Chart service not available: {e}")

        self.vision_analyzer = get_vision_analyzer()
        self.ai_service = AIService()
        self._initialized = True

    async def analyze(
        self,
        symbol: str,
        mode: AnalysisMode = AnalysisMode.STANDARD,
        current_price: Optional[float] = None,
    ) -> MultiTimeframeResult:
        """
        Run complete multi-timeframe analysis.

        Args:
            symbol: Trading symbol (e.g., "EUR/USD")
            mode: Analysis depth mode
            current_price: Current market price (optional)

        Returns:
            Complete multi-timeframe analysis result
        """
        await self.initialize()

        start_time = datetime.now()
        config = self.MODE_CONFIG[mode]
        timeframes = config["timeframes"]

        result = MultiTimeframeResult(
            symbol=symbol,
            timestamp=start_time,
            mode=mode,
            final_direction="HOLD",
            final_confidence=0,
        )

        # Collect all tasks
        tasks = []

        # 1. Text-based AI analysis (for each timeframe)
        for tf in timeframes:
            tasks.append(self._run_text_analysis(symbol, tf, config["text_models"]))

        # 2. Vision-based AI analysis (if enabled)
        if config["use_vision"] and self.chart_service:
            tasks.append(self._run_vision_analysis(symbol, timeframes))

        # Run all analyses in parallel
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            result.errors.append(f"Analysis failed: {str(e)}")
            return result

        # Process text analysis results
        text_results = results[:len(timeframes)]
        all_text_votes = []

        for i, tf_result in enumerate(text_results):
            if isinstance(tf_result, Exception):
                result.errors.append(f"Text analysis for {timeframes[i]} failed: {str(tf_result)}")
                continue

            if tf_result:
                all_text_votes.extend(tf_result.get("votes", []))
                result.text_model_votes.extend(tf_result.get("votes", []))

                # Store timeframe analysis
                if "analysis" in tf_result:
                    result.timeframe_analyses[timeframes[i]] = tf_result["analysis"]

        # Process vision analysis results
        if config["use_vision"] and len(results) > len(timeframes):
            vision_result = results[-1]
            if not isinstance(vision_result, Exception) and vision_result:
                result.vision_model_votes = vision_result.get("votes", [])
                all_text_votes.extend(vision_result.get("votes", []))

        # Run consensus voting
        if all_text_votes:
            consensus = self._calculate_consensus(all_text_votes)
            result.final_direction = consensus["direction"]
            result.final_confidence = consensus["confidence"]
            result.stop_loss = consensus.get("stop_loss")
            result.take_profit = consensus.get("take_profit")
            result.risk_reward_ratio = consensus.get("risk_reward")
            result.confluence_score = self._calculate_confluence(result.timeframe_analyses)

        # Calculate position size based on confidence and risk
        if result.final_confidence >= 70:
            result.position_size_percent = self._calculate_position_size(
                confidence=result.final_confidence,
                risk_reward=result.risk_reward_ratio
            )

        result.total_models_used = len(all_text_votes)
        result.total_latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return result

    async def _run_text_analysis(
        self,
        symbol: str,
        timeframe: str,
        models: List[str]
    ) -> Dict[str, Any]:
        """Run text-based AI analysis for a single timeframe."""
        try:
            # Use existing AI service for text analysis
            if self.ai_service:
                result = await self.ai_service.analyze(
                    symbol=symbol,
                    timeframe=timeframe,
                )
                return {
                    "votes": result.get("individual_results", []),
                    "analysis": TimeframeAnalysis(
                        timeframe=timeframe,
                        direction=result.get("consensus", {}).get("direction", "HOLD"),
                        confidence=result.get("consensus", {}).get("confidence", 0),
                        indicators=result.get("indicators", {}),
                        patterns=result.get("patterns", []),
                        support_levels=result.get("support_levels", []),
                        resistance_levels=result.get("resistance_levels", []),
                    )
                }
        except Exception as e:
            return {"votes": [], "error": str(e)}

        return {"votes": []}

    async def _run_vision_analysis(
        self,
        symbol: str,
        timeframes: List[str]
    ) -> Dict[str, Any]:
        """Run vision-based AI analysis across multiple timeframes."""
        if not self.chart_service or not self.vision_analyzer:
            return {"votes": []}

        try:
            # Generate charts for all timeframes
            charts = await self.chart_service.generate_multi_timeframe_charts(
                symbol=symbol,
                timeframes=timeframes
            )

            # Create vision prompt
            prompt = self.chart_service.create_vision_prompt(
                symbol=symbol,
                timeframes=timeframes
            )

            # Run vision analysis on all models
            vision_results = await self.vision_analyzer.analyze_all_models(
                images_base64=charts,
                prompt=prompt
            )

            # Convert to vote format
            votes = []
            for vr in vision_results:
                if not vr.error:
                    votes.append({
                        "provider": f"vision_{vr.model}",
                        "direction": vr.direction,
                        "confidence": vr.confidence,
                        "stop_loss": vr.stop_loss,
                        "take_profit": vr.take_profit[0] if vr.take_profit else None,
                        "reasoning": vr.reasoning,
                        "patterns": vr.patterns_detected,
                        "latency_ms": vr.latency_ms,
                    })

            return {"votes": votes}

        except Exception as e:
            return {"votes": [], "error": str(e)}

    def _calculate_consensus(self, votes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate consensus from all votes."""
        if not votes:
            return {"direction": "HOLD", "confidence": 0}

        # Count directions
        direction_counts = {"LONG": 0, "SHORT": 0, "HOLD": 0}
        direction_confidence = {"LONG": [], "SHORT": [], "HOLD": []}
        stop_losses = []
        take_profits = []

        for vote in votes:
            direction = vote.get("direction", "HOLD")
            confidence = vote.get("confidence", 50)

            direction_counts[direction] += 1
            direction_confidence[direction].append(confidence)

            if vote.get("stop_loss"):
                stop_losses.append(vote["stop_loss"])
            if vote.get("take_profit"):
                take_profits.append(vote["take_profit"])

        # Find winning direction
        winning_direction = max(direction_counts, key=direction_counts.get)
        total_votes = len(votes)

        # Calculate consensus confidence
        vote_ratio = direction_counts[winning_direction] / total_votes
        avg_confidence = (
            sum(direction_confidence[winning_direction]) /
            len(direction_confidence[winning_direction])
            if direction_confidence[winning_direction] else 0
        )

        # Combined confidence = vote ratio * average confidence
        consensus_confidence = vote_ratio * avg_confidence

        # Average stop loss and take profit
        avg_sl = sum(stop_losses) / len(stop_losses) if stop_losses else None
        avg_tp = sum(take_profits) / len(take_profits) if take_profits else None

        # Calculate risk/reward
        risk_reward = None
        if avg_sl and avg_tp:
            # This is simplified - in production would need current price
            risk_reward = 2.0  # Placeholder

        return {
            "direction": winning_direction,
            "confidence": round(consensus_confidence, 2),
            "stop_loss": round(avg_sl, 5) if avg_sl else None,
            "take_profit": [round(avg_tp, 5)] if avg_tp else None,
            "risk_reward": risk_reward,
            "vote_breakdown": direction_counts,
        }

    def _calculate_confluence(self, timeframe_analyses: Dict[str, TimeframeAnalysis]) -> float:
        """
        Calculate confluence score based on timeframe alignment.

        Returns a score from 0-100 indicating how aligned the timeframes are.
        """
        if not timeframe_analyses:
            return 0

        directions = [ta.direction for ta in timeframe_analyses.values()]
        if not directions:
            return 0

        # Count most common direction
        direction_counts = {}
        for d in directions:
            direction_counts[d] = direction_counts.get(d, 0) + 1

        max_count = max(direction_counts.values())
        confluence = (max_count / len(directions)) * 100

        return round(confluence, 2)

    def _calculate_position_size(
        self,
        confidence: float,
        risk_reward: Optional[float] = None,
        max_risk_percent: float = 2.0
    ) -> float:
        """
        Calculate position size as percentage of account.

        Based on confidence and risk/reward ratio.
        """
        # Base position size scaled by confidence
        base_size = (confidence / 100) * max_risk_percent

        # Boost for good risk/reward
        if risk_reward and risk_reward >= 2:
            base_size *= 1.2
        elif risk_reward and risk_reward >= 3:
            base_size *= 1.5

        # Cap at max risk
        return min(base_size, max_risk_percent)


# Singleton instance
_mtf_analyzer: Optional[MultiTimeframeAnalyzer] = None


def get_multi_timeframe_analyzer() -> MultiTimeframeAnalyzer:
    """Get or create the multi-timeframe analyzer singleton."""
    global _mtf_analyzer
    if _mtf_analyzer is None:
        _mtf_analyzer = MultiTimeframeAnalyzer()
    return _mtf_analyzer
