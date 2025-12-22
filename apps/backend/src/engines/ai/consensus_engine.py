"""
Consensus Engine

Aggregates analysis from multiple AI providers and produces a unified trading decision
based on weighted voting, confidence levels, and agreement metrics.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple
import statistics

from src.engines.ai.base_ai import AIAnalysis, TradeDirection


class ConsensusMethod(str, Enum):
    """Methods for calculating consensus."""
    MAJORITY = "majority"  # Simple majority voting
    WEIGHTED = "weighted"  # Weighted by confidence
    CONFIDENCE_THRESHOLD = "confidence_threshold"  # Only count high-confidence votes
    UNANIMOUS = "unanimous"  # All must agree
    SUPERMAJORITY = "supermajority"  # 2/3 must agree


class AgreementLevel(str, Enum):
    """Level of agreement among AI providers."""
    UNANIMOUS = "unanimous"  # 100% agree
    STRONG = "strong"  # >= 80% agree
    MODERATE = "moderate"  # >= 60% agree
    WEAK = "weak"  # >= 40% agree
    SPLIT = "split"  # < 40% agree


@dataclass
class ProviderVote:
    """Individual vote from an AI provider."""
    provider_name: str
    model_name: str
    direction: TradeDirection
    confidence: float
    weight: float = 1.0
    reasoning: str = ""
    is_valid: bool = True
    error: Optional[str] = None


@dataclass
class ConsensusResult:
    """Result of the consensus voting process."""
    # Final decision
    direction: TradeDirection
    confidence: float
    should_trade: bool

    # Voting statistics
    total_votes: int
    valid_votes: int
    votes_for: int
    votes_against: int
    votes_hold: int

    # Agreement metrics
    agreement_level: AgreementLevel
    agreement_percentage: float

    # Weighted analysis
    weighted_confidence: float
    confidence_std_dev: float

    # Price levels (aggregated from providers)
    suggested_entry: Optional[Decimal] = None
    suggested_stop_loss: Optional[Decimal] = None
    suggested_take_profit: Optional[Decimal] = None
    suggested_risk_reward: Optional[float] = None

    # Individual analyses
    individual_votes: List[ProviderVote] = field(default_factory=list)

    # Aggregated insights
    key_factors: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    reasoning_summary: str = ""

    # Costs
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    total_processing_time_ms: int = 0

    # Metadata
    providers_used: List[str] = field(default_factory=list)
    failed_providers: List[str] = field(default_factory=list)


class ConsensusEngine:
    """
    Multi-AI Consensus Engine

    Aggregates trading signals from multiple AI providers and produces
    a unified decision based on configurable voting methods.
    """

    def __init__(
        self,
        method: ConsensusMethod = ConsensusMethod.WEIGHTED,
        min_confidence_threshold: float = 50.0,
        min_agreement_threshold: float = 0.6,
        require_risk_reward: bool = True,
        min_risk_reward: float = 1.5,
    ):
        """
        Initialize the consensus engine.

        Args:
            method: Voting method to use
            min_confidence_threshold: Minimum confidence to count a vote (0-100)
            min_agreement_threshold: Minimum agreement percentage to execute (0-1)
            require_risk_reward: Whether to require valid risk/reward
            min_risk_reward: Minimum acceptable risk/reward ratio
        """
        self.method = method
        self.min_confidence_threshold = min_confidence_threshold
        self.min_agreement_threshold = min_agreement_threshold
        self.require_risk_reward = require_risk_reward
        self.min_risk_reward = min_risk_reward

        # Provider weights (can be customized)
        self._provider_weights: Dict[str, float] = {
            "openai": 1.0,
            "anthropic": 1.0,
            "google": 1.0,
            "groq": 0.9,
            "mistral": 0.9,
            "ollama": 0.8,  # Local models slightly lower weight
        }

    def set_provider_weight(self, provider: str, weight: float) -> None:
        """Set custom weight for a provider."""
        self._provider_weights[provider] = weight

    def calculate_consensus(
        self,
        analyses: List[AIAnalysis],
    ) -> ConsensusResult:
        """
        Calculate consensus from multiple AI analyses.

        Args:
            analyses: List of AIAnalysis from different providers

        Returns:
            ConsensusResult with unified decision
        """
        # Convert analyses to votes
        votes = self._convert_to_votes(analyses)

        # Filter valid votes
        valid_votes = [v for v in votes if v.is_valid]

        # Calculate direction votes
        direction_counts = self._count_directions(valid_votes)

        # Calculate weighted scores
        weighted_scores = self._calculate_weighted_scores(valid_votes)

        # Determine winning direction based on method
        winning_direction, direction_confidence = self._determine_winner(
            valid_votes, direction_counts, weighted_scores
        )

        # Calculate agreement metrics
        agreement_pct = self._calculate_agreement(valid_votes, winning_direction)
        agreement_level = self._get_agreement_level(agreement_pct)

        # Aggregate price levels
        entry, sl, tp, rr = self._aggregate_price_levels(
            valid_votes, analyses, winning_direction
        )

        # Aggregate insights
        key_factors = self._aggregate_factors(analyses, winning_direction)
        risks = self._aggregate_risks(analyses)
        reasoning = self._summarize_reasoning(analyses, winning_direction)

        # Calculate confidence statistics
        confidences = [v.confidence for v in valid_votes]
        avg_confidence = statistics.mean(confidences) if confidences else 0
        std_dev = statistics.stdev(confidences) if len(confidences) > 1 else 0

        # Determine if we should trade
        should_trade = self._should_execute_trade(
            winning_direction,
            direction_confidence,
            agreement_pct,
            rr,
        )

        # Calculate totals
        total_cost = sum(a.cost_usd for a in analyses if a.cost_usd)
        total_tokens = sum(a.tokens_used for a in analyses if a.tokens_used)
        total_time = sum(a.processing_time_ms for a in analyses if a.processing_time_ms)

        return ConsensusResult(
            direction=winning_direction,
            confidence=direction_confidence,
            should_trade=should_trade,
            total_votes=len(votes),
            valid_votes=len(valid_votes),
            votes_for=direction_counts.get(TradeDirection.BUY, 0),
            votes_against=direction_counts.get(TradeDirection.SELL, 0),
            votes_hold=direction_counts.get(TradeDirection.HOLD, 0),
            agreement_level=agreement_level,
            agreement_percentage=agreement_pct,
            weighted_confidence=avg_confidence,
            confidence_std_dev=std_dev,
            suggested_entry=entry,
            suggested_stop_loss=sl,
            suggested_take_profit=tp,
            suggested_risk_reward=rr,
            individual_votes=votes,
            key_factors=key_factors,
            risks=risks,
            reasoning_summary=reasoning,
            total_cost_usd=total_cost,
            total_tokens=total_tokens,
            total_processing_time_ms=total_time,
            providers_used=[v.provider_name for v in valid_votes],
            failed_providers=[v.provider_name for v in votes if not v.is_valid],
        )

    def _convert_to_votes(self, analyses: List[AIAnalysis]) -> List[ProviderVote]:
        """Convert AIAnalysis objects to ProviderVotes."""
        votes = []
        for analysis in analyses:
            # Check if analysis has error
            is_valid = not (
                analysis.reasoning.startswith("Error:") or
                analysis.confidence == 0
            )

            weight = self._provider_weights.get(analysis.provider_name, 1.0)

            vote = ProviderVote(
                provider_name=analysis.provider_name,
                model_name=analysis.model_name,
                direction=analysis.direction,
                confidence=analysis.confidence,
                weight=weight,
                reasoning=analysis.reasoning,
                is_valid=is_valid,
                error=analysis.reasoning if not is_valid else None,
            )
            votes.append(vote)

        return votes

    def _count_directions(
        self, votes: List[ProviderVote]
    ) -> Dict[TradeDirection, int]:
        """Count votes for each direction."""
        counts: Dict[TradeDirection, int] = defaultdict(int)
        for vote in votes:
            if vote.confidence >= self.min_confidence_threshold:
                counts[vote.direction] += 1
        return dict(counts)

    def _calculate_weighted_scores(
        self, votes: List[ProviderVote]
    ) -> Dict[TradeDirection, float]:
        """Calculate weighted scores for each direction."""
        scores: Dict[TradeDirection, float] = defaultdict(float)

        for vote in votes:
            if vote.confidence >= self.min_confidence_threshold:
                # Weight = provider_weight * confidence
                weighted_vote = vote.weight * (vote.confidence / 100)
                scores[vote.direction] += weighted_vote

        return dict(scores)

    def _determine_winner(
        self,
        votes: List[ProviderVote],
        direction_counts: Dict[TradeDirection, int],
        weighted_scores: Dict[TradeDirection, float],
    ) -> Tuple[TradeDirection, float]:
        """Determine the winning direction based on voting method."""

        if not votes:
            return TradeDirection.HOLD, 0.0

        if self.method == ConsensusMethod.MAJORITY:
            # Simple majority wins
            if not direction_counts:
                return TradeDirection.HOLD, 0.0
            winner = max(direction_counts, key=direction_counts.get)
            confidence = (direction_counts[winner] / len(votes)) * 100
            return winner, confidence

        elif self.method == ConsensusMethod.WEIGHTED:
            # Highest weighted score wins
            if not weighted_scores:
                return TradeDirection.HOLD, 0.0
            winner = max(weighted_scores, key=weighted_scores.get)
            total_weight = sum(weighted_scores.values())
            confidence = (weighted_scores[winner] / total_weight * 100) if total_weight > 0 else 0
            return winner, confidence

        elif self.method == ConsensusMethod.CONFIDENCE_THRESHOLD:
            # Only high-confidence votes count
            high_conf_votes = [v for v in votes if v.confidence >= 70]
            if not high_conf_votes:
                return TradeDirection.HOLD, 0.0

            counts: Dict[TradeDirection, int] = defaultdict(int)
            for v in high_conf_votes:
                counts[v.direction] += 1

            winner = max(counts, key=counts.get)
            confidence = (counts[winner] / len(high_conf_votes)) * 100
            return winner, confidence

        elif self.method == ConsensusMethod.UNANIMOUS:
            # All must agree
            directions = set(v.direction for v in votes)
            if len(directions) == 1:
                winner = list(directions)[0]
                avg_conf = statistics.mean(v.confidence for v in votes)
                return winner, avg_conf
            return TradeDirection.HOLD, 0.0

        elif self.method == ConsensusMethod.SUPERMAJORITY:
            # 2/3 must agree
            if not direction_counts:
                return TradeDirection.HOLD, 0.0

            winner = max(direction_counts, key=direction_counts.get)
            agreement = direction_counts[winner] / len(votes)

            if agreement >= 0.67:
                relevant_votes = [v for v in votes if v.direction == winner]
                avg_conf = statistics.mean(v.confidence for v in relevant_votes)
                return winner, avg_conf
            return TradeDirection.HOLD, 0.0

        return TradeDirection.HOLD, 0.0

    def _calculate_agreement(
        self, votes: List[ProviderVote], winner: TradeDirection
    ) -> float:
        """Calculate what percentage agrees with the winner."""
        if not votes:
            return 0.0

        agreeing = sum(1 for v in votes if v.direction == winner)
        return agreeing / len(votes)

    def _get_agreement_level(self, agreement_pct: float) -> AgreementLevel:
        """Categorize the agreement level."""
        if agreement_pct >= 1.0:
            return AgreementLevel.UNANIMOUS
        elif agreement_pct >= 0.8:
            return AgreementLevel.STRONG
        elif agreement_pct >= 0.6:
            return AgreementLevel.MODERATE
        elif agreement_pct >= 0.4:
            return AgreementLevel.WEAK
        else:
            return AgreementLevel.SPLIT

    def _aggregate_price_levels(
        self,
        votes: List[ProviderVote],
        analyses: List[AIAnalysis],
        direction: TradeDirection,
    ) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal], Optional[float]]:
        """Aggregate entry, SL, TP from analyses that agree with direction."""

        # Filter analyses that agree with winning direction
        agreeing = [
            a for a in analyses
            if a.direction == direction and not a.reasoning.startswith("Error:")
        ]

        if not agreeing:
            return None, None, None, None

        # Collect valid values
        entries = [a.entry_price for a in agreeing if a.entry_price]
        stop_losses = [a.stop_loss for a in agreeing if a.stop_loss]
        take_profits = [a.take_profit for a in agreeing if a.take_profit]
        risk_rewards = [a.risk_reward_ratio for a in agreeing if a.risk_reward_ratio]

        # Calculate median (more robust than mean for prices)
        entry = self._median_decimal(entries) if entries else None
        sl = self._median_decimal(stop_losses) if stop_losses else None
        tp = self._median_decimal(take_profits) if take_profits else None
        rr = statistics.median(risk_rewards) if risk_rewards else None

        return entry, sl, tp, rr

    def _median_decimal(self, values: List[Decimal]) -> Decimal:
        """Calculate median of Decimal values."""
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        if n % 2 == 1:
            return sorted_vals[n // 2]
        else:
            return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2

    def _aggregate_factors(
        self, analyses: List[AIAnalysis], direction: TradeDirection
    ) -> List[str]:
        """Aggregate key factors from agreeing analyses."""
        factor_counts: Dict[str, int] = defaultdict(int)

        for analysis in analyses:
            if analysis.direction == direction:
                for factor in analysis.key_factors:
                    # Normalize factor text
                    normalized = factor.strip().lower()
                    factor_counts[factor] += 1

        # Sort by frequency and return top factors
        sorted_factors = sorted(
            factor_counts.items(), key=lambda x: x[1], reverse=True
        )
        return [f[0] for f in sorted_factors[:5]]

    def _aggregate_risks(self, analyses: List[AIAnalysis]) -> List[str]:
        """Aggregate risks from all analyses."""
        risk_counts: Dict[str, int] = defaultdict(int)

        for analysis in analyses:
            for risk in analysis.risks:
                normalized = risk.strip().lower()
                risk_counts[risk] += 1

        # Sort by frequency and return top risks
        sorted_risks = sorted(
            risk_counts.items(), key=lambda x: x[1], reverse=True
        )
        return [r[0] for r in sorted_risks[:5]]

    def _summarize_reasoning(
        self, analyses: List[AIAnalysis], direction: TradeDirection
    ) -> str:
        """Create a summary of reasoning from agreeing analyses."""
        agreeing = [
            a for a in analyses
            if a.direction == direction and a.reasoning and not a.reasoning.startswith("Error:")
        ]

        if not agreeing:
            return "No consensus reached."

        if len(agreeing) == 1:
            return agreeing[0].reasoning

        # Combine reasonings
        providers = [a.model_name for a in agreeing]
        sample_reasoning = agreeing[0].reasoning[:200]  # First 200 chars

        return (
            f"Consensus from {len(agreeing)} models ({', '.join(providers[:3])}{'...' if len(providers) > 3 else ''}). "
            f"{sample_reasoning}..."
        )

    def _should_execute_trade(
        self,
        direction: TradeDirection,
        confidence: float,
        agreement: float,
        risk_reward: Optional[float],
    ) -> bool:
        """Determine if conditions are met to execute the trade."""

        # Never trade on HOLD
        if direction == TradeDirection.HOLD:
            return False

        # Check confidence threshold
        if confidence < self.min_confidence_threshold:
            return False

        # Check agreement threshold
        if agreement < self.min_agreement_threshold:
            return False

        # Check risk/reward if required
        if self.require_risk_reward:
            if risk_reward is None or risk_reward < self.min_risk_reward:
                return False

        return True


# Factory function
def create_consensus_engine(
    method: str = "weighted",
    **kwargs
) -> ConsensusEngine:
    """Create a consensus engine with the specified method."""
    consensus_method = ConsensusMethod(method)
    return ConsensusEngine(method=consensus_method, **kwargs)
