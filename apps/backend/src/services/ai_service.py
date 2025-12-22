"""
AI Service Orchestrator

Orchestrates multiple AI providers to run analysis in parallel
and produces consensus-based trading decisions.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Type

from src.core.config import settings
from src.engines.ai.base_ai import AIAnalysis, BaseAIProvider, MarketContext, TradeDirection
from src.engines.ai.consensus_engine import (
    ConsensusEngine,
    ConsensusMethod,
    ConsensusResult,
    create_consensus_engine,
)
from src.engines.ai.providers import (
    AnthropicProvider,
    GoogleProvider,
    GroqProvider,
    MistralProvider,
    OllamaProvider,
    OpenAIProvider,
)


@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""
    provider_class: Type[BaseAIProvider]
    model_name: str
    enabled: bool = True
    weight: float = 1.0
    api_key: Optional[str] = None
    extra_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIServiceConfig:
    """Configuration for the AI Service."""
    # Consensus settings
    consensus_method: ConsensusMethod = ConsensusMethod.WEIGHTED
    min_confidence_threshold: float = 50.0
    min_agreement_threshold: float = 0.6
    require_risk_reward: bool = True
    min_risk_reward: float = 1.5

    # Execution settings
    parallel_execution: bool = True
    timeout_seconds: float = 60.0
    retry_failed: bool = True
    max_retries: int = 2

    # Provider settings
    providers: List[ProviderConfig] = field(default_factory=list)


# Default provider configurations
DEFAULT_PROVIDERS = [
    # OpenAI - GPT-4o (high quality)
    ProviderConfig(
        provider_class=OpenAIProvider,
        model_name="gpt-4o",
        weight=1.0,
    ),
    # OpenAI - GPT-4o-mini (fast, cost-effective)
    ProviderConfig(
        provider_class=OpenAIProvider,
        model_name="gpt-4o-mini",
        weight=0.9,
    ),
    # Anthropic - Claude Sonnet
    ProviderConfig(
        provider_class=AnthropicProvider,
        model_name="claude-sonnet",
        weight=1.0,
    ),
    # Anthropic - Claude Haiku (fast)
    ProviderConfig(
        provider_class=AnthropicProvider,
        model_name="claude-haiku",
        weight=0.85,
    ),
    # Google - Gemini Flash (fast)
    ProviderConfig(
        provider_class=GoogleProvider,
        model_name="gemini-flash",
        weight=0.9,
    ),
    # Groq - Llama 3.3 (ultra-fast!)
    ProviderConfig(
        provider_class=GroqProvider,
        model_name="llama3-70b",
        weight=0.95,
    ),
    # Groq - Llama 8B (fastest)
    ProviderConfig(
        provider_class=GroqProvider,
        model_name="llama3-8b",
        weight=0.8,
    ),
    # Mistral - Large
    ProviderConfig(
        provider_class=MistralProvider,
        model_name="mistral-large",
        weight=0.9,
    ),
    # Mistral - Small (fast)
    ProviderConfig(
        provider_class=MistralProvider,
        model_name="mistral-small",
        weight=0.8,
    ),
    # Ollama - Local (free!)
    ProviderConfig(
        provider_class=OllamaProvider,
        model_name="llama3.1:8b",
        weight=0.75,
        enabled=False,  # Disabled by default (requires local setup)
    ),
]


class AIService:
    """
    AI Service Orchestrator

    Manages multiple AI providers, runs them in parallel,
    and produces consensus-based trading decisions.
    """

    def __init__(self, config: Optional[AIServiceConfig] = None):
        """
        Initialize AI Service.

        Args:
            config: Service configuration. Uses defaults if not provided.
        """
        self.config = config or AIServiceConfig()

        # Use default providers if none configured
        if not self.config.providers:
            self.config.providers = DEFAULT_PROVIDERS

        # Initialize providers
        self._providers: Dict[str, BaseAIProvider] = {}
        self._initialize_providers()

        # Initialize consensus engine
        self._consensus_engine = create_consensus_engine(
            method=self.config.consensus_method.value,
            min_confidence_threshold=self.config.min_confidence_threshold,
            min_agreement_threshold=self.config.min_agreement_threshold,
            require_risk_reward=self.config.require_risk_reward,
            min_risk_reward=self.config.min_risk_reward,
        )

    def _initialize_providers(self) -> None:
        """Initialize enabled AI providers."""
        for provider_config in self.config.providers:
            if not provider_config.enabled:
                continue

            try:
                # Create provider instance
                provider = provider_config.provider_class(
                    model_name=provider_config.model_name,
                    api_key=provider_config.api_key,
                    **provider_config.extra_config,
                )

                # Set weight in consensus engine
                self._consensus_engine.set_provider_weight(
                    provider.provider_name,
                    provider_config.weight,
                )

                # Store provider with unique key
                key = f"{provider.provider_name}_{provider_config.model_name}"
                self._providers[key] = provider

            except Exception as e:
                print(f"Failed to initialize provider {provider_config.model_name}: {e}")

    @property
    def provider_count(self) -> int:
        """Get number of active providers."""
        return len(self._providers)

    @property
    def provider_names(self) -> List[str]:
        """Get list of active provider names."""
        return list(self._providers.keys())

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all providers."""
        results = {}

        async def check_provider(key: str, provider: BaseAIProvider) -> Tuple[str, bool]:
            try:
                healthy = await provider.health_check()
                return key, healthy
            except Exception:
                return key, False

        tasks = [
            check_provider(key, provider)
            for key, provider in self._providers.items()
        ]

        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for result in completed:
            if isinstance(result, tuple):
                key, healthy = result
                results[key] = healthy
            else:
                # Exception occurred
                pass

        return results

    async def analyze(
        self,
        context: MarketContext,
        providers: Optional[List[str]] = None,
    ) -> ConsensusResult:
        """
        Run analysis across all (or selected) AI providers.

        Args:
            context: Market context with all relevant data
            providers: Optional list of provider keys to use.
                      Uses all if not specified.

        Returns:
            ConsensusResult with aggregated decision
        """
        # Select providers
        if providers:
            selected = {k: v for k, v in self._providers.items() if k in providers}
        else:
            selected = self._providers

        if not selected:
            raise ValueError("No providers available for analysis")

        # Run analyses
        if self.config.parallel_execution:
            analyses = await self._run_parallel(context, selected)
        else:
            analyses = await self._run_sequential(context, selected)

        # Calculate consensus
        result = self._consensus_engine.calculate_consensus(analyses)

        return result

    async def _run_parallel(
        self,
        context: MarketContext,
        providers: Dict[str, BaseAIProvider],
    ) -> List[AIAnalysis]:
        """Run all providers in parallel."""

        async def analyze_with_provider(
            key: str, provider: BaseAIProvider
        ) -> AIAnalysis:
            try:
                return await asyncio.wait_for(
                    provider.analyze(context),
                    timeout=self.config.timeout_seconds,
                )
            except asyncio.TimeoutError:
                return AIAnalysis(
                    provider_name=provider.provider_name,
                    model_name=provider.model_name,
                    direction=TradeDirection.HOLD,
                    confidence=0,
                    reasoning=f"Error: Timeout after {self.config.timeout_seconds}s",
                    key_factors=[],
                    risks=[],
                )
            except Exception as e:
                return AIAnalysis(
                    provider_name=provider.provider_name,
                    model_name=provider.model_name,
                    direction=TradeDirection.HOLD,
                    confidence=0,
                    reasoning=f"Error: {str(e)}",
                    key_factors=[],
                    risks=[],
                )

        tasks = [
            analyze_with_provider(key, provider)
            for key, provider in providers.items()
        ]

        analyses = await asyncio.gather(*tasks)

        # Retry failed if configured
        if self.config.retry_failed:
            failed_indices = [
                i for i, a in enumerate(analyses)
                if a.reasoning.startswith("Error:")
            ]

            for attempt in range(self.config.max_retries):
                if not failed_indices:
                    break

                retry_tasks = [
                    analyze_with_provider(
                        list(providers.keys())[i],
                        list(providers.values())[i],
                    )
                    for i in failed_indices
                ]

                retry_results = await asyncio.gather(*retry_tasks)

                # Update analyses with successful retries
                new_failed = []
                for idx, (orig_idx, result) in enumerate(zip(failed_indices, retry_results)):
                    if not result.reasoning.startswith("Error:"):
                        analyses[orig_idx] = result
                    else:
                        new_failed.append(orig_idx)

                failed_indices = new_failed

        return list(analyses)

    async def _run_sequential(
        self,
        context: MarketContext,
        providers: Dict[str, BaseAIProvider],
    ) -> List[AIAnalysis]:
        """Run providers sequentially."""
        analyses = []

        for key, provider in providers.items():
            try:
                analysis = await asyncio.wait_for(
                    provider.analyze(context),
                    timeout=self.config.timeout_seconds,
                )
                analyses.append(analysis)
            except Exception as e:
                analyses.append(AIAnalysis(
                    provider_name=provider.provider_name,
                    model_name=provider.model_name,
                    direction=TradeDirection.HOLD,
                    confidence=0,
                    reasoning=f"Error: {str(e)}",
                    key_factors=[],
                    risks=[],
                ))

        return analyses

    async def quick_analyze(
        self,
        context: MarketContext,
    ) -> ConsensusResult:
        """
        Quick analysis using only the fastest providers.

        Uses Groq (ultra-fast) and GPT-4o-mini for rapid decisions.
        Good for real-time scalping scenarios.
        """
        fast_providers = [
            "groq_llama3-70b",
            "groq_llama3-8b",
            "openai_gpt-4o-mini",
            "anthropic_claude-haiku",
        ]

        available = [p for p in fast_providers if p in self._providers]

        if not available:
            # Fall back to first available
            available = list(self._providers.keys())[:3]

        return await self.analyze(context, providers=available)

    async def premium_analyze(
        self,
        context: MarketContext,
    ) -> ConsensusResult:
        """
        Premium analysis using highest quality providers.

        Uses GPT-4o, Claude Sonnet, Gemini Pro for best accuracy.
        Better for swing trading and important decisions.
        """
        premium_providers = [
            "openai_gpt-4o",
            "anthropic_claude-sonnet",
            "google_gemini-flash",
            "mistral_mistral-large",
            "groq_llama3-70b",
        ]

        available = [p for p in premium_providers if p in self._providers]

        if not available:
            available = list(self._providers.keys())

        return await self.analyze(context, providers=available)

    def enable_provider(self, provider_key: str) -> bool:
        """Enable a disabled provider."""
        for config in self.config.providers:
            key = f"{config.provider_class.__name__.replace('Provider', '').lower()}_{config.model_name}"
            if key == provider_key and not config.enabled:
                config.enabled = True
                self._initialize_providers()
                return True
        return False

    def disable_provider(self, provider_key: str) -> bool:
        """Disable an active provider."""
        if provider_key in self._providers:
            del self._providers[provider_key]
            for config in self.config.providers:
                key = f"{config.provider_class.__name__.replace('Provider', '').lower()}_{config.model_name}"
                if key == provider_key:
                    config.enabled = False
            return True
        return False

    def get_provider_stats(self) -> Dict[str, Any]:
        """Get statistics about configured providers."""
        enabled = [c for c in self.config.providers if c.enabled]
        disabled = [c for c in self.config.providers if not c.enabled]

        return {
            "total_configured": len(self.config.providers),
            "enabled": len(enabled),
            "disabled": len(disabled),
            "active_providers": list(self._providers.keys()),
            "consensus_method": self.config.consensus_method.value,
            "min_confidence": self.config.min_confidence_threshold,
            "min_agreement": self.config.min_agreement_threshold,
        }


# Singleton instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or create AI Service singleton."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service


async def create_market_context(
    symbol: str,
    timeframe: str,
    current_price: Decimal,
    indicators: Dict[str, Any],
    candles: Optional[List[Dict[str, Any]]] = None,
    news_sentiment: Optional[float] = None,
    market_session: Optional[str] = None,
    economic_events: Optional[List[Dict[str, Any]]] = None,
    support_levels: Optional[List[Decimal]] = None,
    resistance_levels: Optional[List[Decimal]] = None,
) -> MarketContext:
    """
    Helper to create MarketContext from trading data.

    This is a convenience function to build the context
    object required by AI providers.
    """
    return MarketContext(
        symbol=symbol,
        timeframe=timeframe,
        current_price=current_price,
        indicators=indicators,
        candles=candles or [],
        news_sentiment=news_sentiment,
        market_session=market_session,
        economic_events=economic_events or [],
        support_levels=support_levels or [],
        resistance_levels=resistance_levels or [],
    )
